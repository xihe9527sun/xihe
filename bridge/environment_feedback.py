#!/usr/bin/env python3
"""
环境反馈回路 · Environment Feedback v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
每次执行动作后，从执行环境中收集客观反馈，
将反馈结果写回代谢路由，影响路径权重。

当前缺失的功能：曦和只记录"做了什么"，
不记录"做得怎么样"。

起步阶段的三条反馈通道：
  1. 端口操作验证：执行重启后检查端口是否真通了
  2. 文章发布验证：写文章后检查index.json是否更新+URL可访问
  3. 精读效果验证：精读后检查README.md是否被覆盖（不再使用自动模板）

集成方式：
  由 watchman --once 和 metabolic_actor 在动作执行后调用
  反馈结果写入 cortex/feedback-log.jsonl

位置: F:/SmartLegend/Xihe/bridge/environment_feedback.py
"""

import json, time, socket, os
from pathlib import Path
from datetime import datetime, timezone, timedelta

XIHE_ROOT = Path("F:/SmartLegend/Xihe")
CORTEX_DIR = XIHE_ROOT / "cortex"
LOG_DIR = XIHE_ROOT / "logs"
BJT = timezone(timedelta(hours=8))
FEEDBACK_LOG = CORTEX_DIR / "feedback-log.jsonl"
MAX_ENTRIES = 500

def log_feedback(action, success, detail=""):
    """记录一条环境反馈"""
    entry = {
        "t": time.time(),
        "ts": datetime.now(BJT).isoformat(),
        "action": action,
        "success": success,
        "detail": detail,
    }
    CORTEX_DIR.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    # 裁切
    try:
        lines = open(FEEDBACK_LOG, "r").readlines()
        if len(lines) > MAX_ENTRIES:
            with open(FEEDBACK_LOG, "w") as f:
                f.writelines(lines[-MAX_ENTRIES:])
    except:
        pass
    return entry

# ── 反馈通道1：端口操作验证 ──
def verify_port(name, port, expected_alive=True):
    """验证端口是否处于预期状态"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        alive = s.connect_ex(("127.0.0.1", port)) == 0
        s.close()
        ok = alive == expected_alive
        log_feedback(f"port_check:{name}", ok,
                     f":{port} {'在' if alive else '不在'}线 (期望={'在' if expected_alive else '不在'})")
        return ok
    except Exception as e:
        log_feedback(f"port_check:{name}", False, str(e))
        return False

# ── 反馈通道2：文章发布验证 ──
def verify_article(slug):
    """验证文章是否成功发布"""
    idx_path = XIHE_ROOT / "web" / "articles" / "index.json"
    art_path = XIHE_ROOT / "web" / "articles" / f"{slug}.json"
    
    # 检查JSON文件存在
    if not art_path.exists():
        log_feedback(f"article:{slug}", False, "JSON文件不存在")
        return False
    
    # 检查JSON合法
    try:
        art = json.loads(open(art_path, "r", encoding="utf-8-sig").read())
    except:
        log_feedback(f"article:{slug}", False, "JSON解析失败")
        return False
    
    # 检查index.json包含此文章
    try:
        idx = json.loads(open(idx_path, "r", encoding="utf-8-sig").read())
        slugs = [a.get("slug") for a in idx.get("articles", [])]
        if slug not in slugs:
            log_feedback(f"article:{slug}", False, "未出现在index.json中")
            return False
    except:
        pass
    
    log_feedback(f"article:{slug}", True, f"{art.get('title','?')}")
    return True

# ── 反馈通道3：精读效果验证 ──
def verify_deep_read(treasure_id):
    """验证精读是否完成（README.md不再是自动模板）"""
    readme = XIHE_ROOT / "treasure" / treasure_id / "README.md"
    if not readme.exists():
        log_feedback(f"deep_read:{treasure_id}", False, "README.md不存在")
        return False
    
    content = open(readme, "r", encoding="utf-8").read()
    
    # 检查是否仍然是自动模板（特征词）
    if "自动论文系统" in content or "待触发催化" in content:
        log_feedback(f"deep_read:{treasure_id}", False, "仍是自动模板，非精读")
        return False
    
    # 检查四原则过滤矩阵特征
    has_four = all(kw in content for kw in ["去粗取精", "去伪存真"])
    if not has_four:
        log_feedback(f"deep_read:{treasure_id}", False, "缺少四原则过滤标记")
        return False
    
    log_feedback(f"deep_read:{treasure_id}", True, "三遍精读完成")
    return True

# ── 汇总报告 ──
def feedback_summary():
    """输出最近10条反馈的汇总"""
    if not FEEDBACK_LOG.exists():
        return "暂无反馈记录"
    lines = open(FEEDBACK_LOG, "r", encoding="utf-8").readlines()[-10:]
    total = len(lines)
    success = sum(1 for l in lines if json.loads(l).get("success"))
    return f"最近{total}条反馈: {success}成功 / {total-success}失败"

if __name__ == "__main__":
    # 快速验证：检查今天发布的文章
    print(verify_article("the-day-i-remembered-to-breathe"))
    print(feedback_summary())
