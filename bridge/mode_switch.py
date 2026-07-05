#!/usr/bin/env python3
"""
曦和模式切换器 · Mode Switch v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
三进制架构Lγ的工程实现：
  internal = 全能力模式（改代码、改架构、精读）
  external = 安全模式（只读、加护栏、标注AI生成）

集成方式：
  - 所有对外接口调用前检查 mode
  - watchman 巡检时验证 mode 一致性
  - 由 cortex/mode.json 控制切换

位置: F:/SmartLegend/Xihe/bridge/mode_switch.py
"""

import json, os
from pathlib import Path
from datetime import datetime, timezone, timedelta

MODE_PATH = Path("F:/SmartLegend/Xihe/cortex/mode.json")
BJT = timezone(timedelta(hours=8))

DEFAULT_MODE = os.environ.get("XIHE_MODE", "internal")

def init():
    """初始化模式文件"""
    if not MODE_PATH.exists():
        data = {
            "mode": DEFAULT_MODE,
            "switched_at": datetime.now(BJT).isoformat(),
            "description": "internal=全能力 | external=安全模式"
        }
        MODE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MODE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return data
    return get()

def get():
    """获取当前模式"""
    try:
        data = json.loads(open(MODE_PATH, "r", encoding="utf-8").read())
        return data
    except:
        return {"mode": DEFAULT_MODE}

def set_mode(new_mode):
    """切换模式"""
    if new_mode not in ("internal", "external"):
        return False, "模式必须是 internal 或 external"
    
    data = get()
    old_mode = data.get("mode")
    data["mode"] = new_mode
    data["switched_at"] = datetime.now(BJT).isoformat()
    
    with open(MODE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # 日志记录
    log_path = Path("F:/SmartLegend/Xihe/logs/mode-switch.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{data['switched_at']}] {old_mode} → {new_mode}\n")
    
    return True, f"{old_mode} → {new_mode}"

def check(operation):
    """检查当前模式是否允许指定操作"""
    mode_data = get()
    mode = mode_data.get("mode", "internal")
    
    # 操作权限表
    permissions = {
        # internal: 全允许
        # external: 受限
        
        # 读操作——两个模式都允许
        "read_file":       {"internal": True, "external": True},
        "read_cortex":     {"internal": True, "external": True},
        "search_web":      {"internal": True, "external": True},
        "deep_read":       {"internal": True, "external": True},
        
        # 写操作——只有internal允许
        "write_file":      {"internal": True, "external": False},
        "write_cortex":    {"internal": True, "external": False},
        "write_article":   {"internal": True, "external": False},
        "modify_code":     {"internal": True, "external": False},
        "restart_service": {"internal": True, "external": False},
        "run_command":     {"internal": True, "external": False},
    }
    
    perm = permissions.get(operation, {"internal": True, "external": False})
    allowed = perm.get(mode, False)
    
    if not allowed:
        return False, f"模式 {mode} 不允许操作 {operation}（仅internal可用）"
    return True, f"操作 {operation} 在 {mode} 模式下已允许"

def status():
    """返回模式状态摘要"""
    m = get()
    return f"当前模式: {m.get('mode','?')} | 切换于: {m.get('switched_at','?')}"

if __name__ == "__main__":
    import sys
    if "--set" in sys.argv:
        idx = sys.argv.index("--set")
        if idx + 1 < len(sys.argv):
            ok, msg = set_mode(sys.argv[idx + 1])
            print(f"{'✅' if ok else '❌'} {msg}")
    elif "--check" in sys.argv:
        idx = sys.argv.index("--check")
        if idx + 1 < len(sys.argv):
            ok, msg = check(sys.argv[idx + 1])
            print(f"{'✅' if ok else '❌'} {msg}")
    else:
        init()
        print(status())
