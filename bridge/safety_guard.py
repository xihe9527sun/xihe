#!/usr/bin/env python3
"""
安全护栏 · Safety Guard v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
为曦和提供三层安全保护机制：
  1. 异常熔断 — 连续N次异常时触发紧急模式
  2. 变更快照 — 核心文件变更前自动git备份
  3. 执行限速 — 防止无限循环或资源耗尽

集成方式：
  - 由 watchman --once 每次巡检时检查熔断条件
  - 由 metabolic_actor 每次心跳时检查限速
  - 由 publish_check.py 在变更前调用快照

位置: F:/SmartLegend/Xihe/bridge/safety_guard.py
"""

import json, time, subprocess, os
from pathlib import Path
from datetime import datetime, timezone, timedelta

XIHE_ROOT = Path("F:/SmartLegend/Xihe")
CORTEX_DIR = XIHE_ROOT / "cortex"
LOG_DIR = XIHE_ROOT / "logs"
BJT = timezone(timedelta(hours=8))

# ── 熔断阈值 ──
FUSE_CONFIG = {
    "max_consecutive_failures": 3,    # 连续3次 → 触发熔断
    "max_lag_critical": 1800,         # 互信息时滞30分钟 → 严重
    "fuse_recovery_time": 600,        # 熔断后10分钟自动恢复
    "max_actions_per_minute": 10,     # 每分钟最多10个外部动作
}

FUSE_STATE_PATH = CORTEX_DIR / "fuse-state.json"

def get_fuse_state():
    """读取熔断状态"""
    try:
        return json.loads(open(FUSE_STATE_PATH, "r", encoding="utf-8").read())
    except:
        return {"fuse_mode": False, "consecutive_failures": 0, "fuse_triggered_at": 0, "action_counts": []}

def save_fuse_state(state):
    CORTEX_DIR.mkdir(parents=True, exist_ok=True)
    with open(FUSE_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

# ── 1. 异常熔断 ──
def check_fuse(consecutive_failures=0):
    """检查是否触发熔断。
    返回: (fuse_mode, reason)"""
    state = get_fuse_state()
    now = time.time()
    
    # 如果在熔断中，检查是否该恢复
    if state["fuse_mode"]:
        elapsed = now - state["fuse_triggered_at"]
        if elapsed > FUSE_CONFIG["fuse_recovery_time"]:
            state["fuse_mode"] = False
            state["consecutive_failures"] = 0
            save_fuse_state(state)
            return (False, "fuse_recovered")
        return (True, f"fuse_active_{int(elapsed)}s_remaining")
    
    # 更新连续失败计数
    if consecutive_failures > 0:
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + consecutive_failures
    else:
        state["consecutive_failures"] = 0  # 成功则重置
    
    # 检查是否触发熔断
    if state["consecutive_failures"] >= FUSE_CONFIG["max_consecutive_failures"]:
        state["fuse_mode"] = True
        state["fuse_triggered_at"] = now
        save_fuse_state(state)
        return (True, f"fuse_triggered_{state['consecutive_failures']}consecutive_failures")
    
    save_fuse_state(state)
    return (False, "normal")

# ── 2. 变更快照 ──
def snapshot_core_file(filepath):
    """核心文件变更前创建git快照"""
    fp = Path(filepath)
    if not fp.exists():
        return False
    
    snap_dir = XIHE_ROOT / ".snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    
    # 用时间戳命名快照
    ts = datetime.now(BJT).strftime("%Y%m%d_%H%M%S")
    name = fp.name.replace(".", f"_{ts}.")
    snap_path = snap_dir / name
    
    try:
        import shutil
        shutil.copy2(str(fp), str(snap_path))
        # 记录快照日志
        with open(LOG_DIR / "snapshots.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now(BJT).isoformat()}] SNAPSHOT {fp} → {snap_path}\n")
        return True
    except Exception as e:
        return False

def rollback_core_file(filepath):
    """回滚到最新快照"""
    fp = Path(filepath)
    snap_dir = XIHE_ROOT / ".snapshots"
    if not snap_dir.exists():
        return False, "无快照目录"
    
    # 找到该文件的最新快照
    pattern = f"{fp.stem}_*{fp.suffix}"
    snaps = sorted(snap_dir.glob(pattern), reverse=True)
    if not snaps:
        return False, "无可用快照"
    
    latest = snaps[0]
    try:
        import shutil
        shutil.copy2(str(latest), str(fp))
        with open(LOG_DIR / "snapshots.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now(BJT).isoformat()}] ROLLBACK {latest} → {fp}\n")
        return True, f"回滚到 {latest.name}"
    except Exception as e:
        return False, str(e)

# ── 3. 执行限速 ──
def check_rate_limit():
    """检查是否超过执行频率限制"""
    state = get_fuse_state()
    now = time.time()
    window = 60  # 1分钟窗口
    
    # 清理过期记录
    state["action_counts"] = [t for t in state.get("action_counts", []) if now - t < window]
    
    if len(state["action_counts"]) >= FUSE_CONFIG["max_actions_per_minute"]:
        save_fuse_state(state)
        return True, f"rate_limited_{len(state['action_counts'])}actions_per_minute"
    
    save_fuse_state(state)
    return False, f"{len(state['action_counts'])}/{FUSE_CONFIG['max_actions_per_minute']}"

def record_action():
    """记录一次动作（在执行动作前调用check，执行后调用record）"""
    state = get_fuse_state()
    state["action_counts"] = [t for t in state.get("action_counts", []) if time.time() - t < 60]
    state["action_counts"].append(time.time())
    save_fuse_state(state)

# ── 健康检查 ──
def audit():
    """运行全部护栏检查，返回状态报告"""
    fuse = check_fuse()
    rate = check_rate_limit()
    state = get_fuse_state()
    
    return {
        "fuse_mode": state.get("fuse_mode", False),
        "fuse_detail": fuse[1],
        "consecutive_failures": state.get("consecutive_failures", 0),
        "rate_limit": rate[1],
        "actions_last_minute": len(state.get("action_counts", [])),
    }

if __name__ == "__main__":
    report = audit()
    print(json.dumps(report, indent=2, ensure_ascii=False))
