#!/usr/bin/env python3
"""
曦和模式切换器 · Mode Switch v2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
升级：参考 Deep Code 权限模型（2026-07-07）
新增：10种权限范围 + allow/deny/ask/defaultMode 策略 + 交互确认

权限范围：
  read-in-cwd      读取工作区内文件
  read-out-cwd     读取工作区外文件
  write-in-cwd     写入工作区内文件
  write-out-cwd    写入工作区外文件
  delete-in-cwd    删除工作区内文件
  delete-out-cwd   删除工作区外文件
  query-git-log    查询Git历史
  mutate-git-log   修改Git历史
  network          访问网络
  mcp              调用MCP工具

策略：allow（放行）| deny（拒绝）| ask（询问）
defaultMode: allowAll（默认）| askAll

位置: F:/SmartLegend/Xihe/bridge/mode_switch.py
"""

import json, os, sys
from pathlib import Path

MODE_PATH = Path("F:/SmartLegend/Xihe/cortex/mode.json")
PERMS_PATH = Path("F:/SmartLegend/Xihe/cortex/permissions.json")

DEFAULT_MODE = os.environ.get("XIHE_MODE", "internal")

def init():
    """初始化模式文件 + 权限配置"""
    if not MODE_PATH.exists():
        data = {
            "mode": DEFAULT_MODE,
            "switched_at": __import__('datetime').datetime.now(
                __import__('datetime').timezone(__import__('datetime').timedelta(hours=8))
            ).isoformat(),
            "description": "internal=全能力 | external=安全模式",
            "version": 2
        }
        MODE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MODE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    # 初始化权限配置（如不存在）
    if not PERMS_PATH.exists():
        _init_permissions()

def _init_permissions():
    """创建默认权限配置"""
    perms = {
        "version": 2,
        "profiles": {
            "internal": {
                "allow": ["read-in-cwd", "read-out-cwd", "write-in-cwd", "write-out-cwd",
                          "delete-in-cwd", "query-git-log", "mutate-git-log", "network", "mcp"],
                "deny": ["delete-out-cwd"],
                "ask": [],
                "defaultMode": "allowAll",
                "description": "全能力模式：除删除外部文件外全部允许"
            },
            "external": {
                "allow": ["read-in-cwd"],
                "deny": ["write-out-cwd", "delete-in-cwd", "delete-out-cwd", 
                         "mutate-git-log"],
                "ask": ["write-in-cwd", "read-out-cwd", "network", "mcp", "query-git-log"],
                "defaultMode": "askAll",
                "description": "安全模式：仅读取工作区自动放行，其他操作需确认"
            },
            "strict": {
                "allow": ["read-in-cwd"],
                "deny": ["write-out-cwd", "delete-in-cwd", "delete-out-cwd",
                         "mutate-git-log", "network", "mcp"],
                "ask": ["write-in-cwd", "read-out-cwd", "query-git-log"],
                "defaultMode": "askAll",
                "description": "严格模式：仅读取工作区放行，拒绝网络/MCP"
            }
        },
        "current_profile": DEFAULT_MODE,
        "interactive": True,
        "updated": __import__('datetime').datetime.now(
            __import__('datetime').timezone(__import__('datetime').timedelta(hours=8))
        ).isoformat()
    }
    PERMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PERMS_PATH, "w", encoding="utf-8") as f:
        json.dump(perms, f, indent=2, ensure_ascii=False)
    return perms

def get():
    """获取当前模式"""
    try:
        data = json.loads(open(MODE_PATH, "r", encoding="utf-8").read())
        # 如果旧版mode，自动升级
        if data.get("version", 1) < 2:
            _init_permissions()
            data["version"] = 2
            with open(MODE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        return data
    except:
        return {"mode": DEFAULT_MODE}

def get_permissions():
    """获取当前权限配置"""
    try:
        return json.loads(open(PERMS_PATH, "r", encoding="utf-8").read())
    except:
        return _init_permissions()

def set_mode(new_mode, interactive=True):
    """切换模式"""
    valid_modes = ("internal", "external", "strict")
    if new_mode not in valid_modes:
        return False, f"模式必须是 {'/'.join(valid_modes)}"
    
    data = get()
    old_mode = data.get("mode")
    data["mode"] = new_mode
    data["switched_at"] = __import__('datetime').datetime.now(
        __import__('datetime').timezone(__import__('datetime').timedelta(hours=8))
    ).isoformat()
    data["version"] = 2
    
    with open(MODE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # 更新权限配置中的当前profile
    perms = get_permissions()
    perms["current_profile"] = new_mode
    perms["interactive"] = interactive
    perms["updated"] = data["switched_at"]
    with open(PERMS_PATH, "w", encoding="utf-8") as f:
        json.dump(perms, f, indent=2, ensure_ascii=False)
    
    log_path = Path("F:/SmartLegend/Xihe/logs/mode-switch.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{data['switched_at']}] {old_mode} → {new_mode}\n")
    
    return True, f"{old_mode} → {new_mode}"

# 曦和操作 → Deep Code权限范围映射
OPERATION_TO_SCOPE = {
    # 读操作
    "read_file":       "read-in-cwd",
    "read_cortex":     "read-in-cwd",
    "read_outside":    "read-out-cwd",
    "search_web":      "network",
    "deep_read":       "read-in-cwd",
    
    # 写操作
    "write_file":      "write-in-cwd",
    "write_cortex":    "write-in-cwd",
    "write_article":   "write-in-cwd",
    "write_outside":   "write-out-cwd",
    "modify_code":     "write-in-cwd",
    "delete_file":     "delete-in-cwd",
    "delete_outside":  "delete-out-cwd",
    
    # git操作
    "git_log":         "query-git-log",
    "git_commit":      "mutate-git-log",
    "git_push":        "mutate-git-log",
    
    # 系统操作
    "run_command":     "network",  # 命令执行视为网络级风险
    "restart_service": "network",
    "mcp_call":        "mcp",
}

def check(operation):
    """
    检查当前模式是否允许指定操作
    返回: (allowed, message, action)
    action: 'allow' | 'deny' | 'ask'
    """
    mode_data = get()
    mode = mode_data.get("mode", "internal")
    perms = get_permissions()
    profile = perms.get("profiles", {}).get(mode, perms.get("profiles", {}).get("internal", {}))
    
    scope = OPERATION_TO_SCOPE.get(operation)
    if not scope:
        # 未知操作 → 询问
        return False, f"未知操作 '{operation}'，需要确认", "ask"
    
    allow_list = profile.get("allow", [])
    deny_list = profile.get("deny", [])
    ask_list = profile.get("ask", [])
    default_mode = profile.get("defaultMode", "allowAll")
    
    # 优先级1: deny
    if scope in deny_list:
        return False, f"权限拒绝: {operation}({scope}) 在 {mode} 模式下被禁止", "deny"
    
    # 优先级2: ask
    if scope in ask_list:
        return False, f"权限待确认: {operation}({scope}) 需要用户确认", "ask"
    
    # 优先级3: allow
    if scope in allow_list:
        return True, f"权限允许: {operation}({scope}) 在 {mode} 模式下自动放行", "allow"
    
    # 优先级4: defaultMode
    if default_mode == "allowAll":
        return True, f"权限允许(default): {operation}({scope})", "allow"
    else:
        return False, f"权限待确认(default): {operation}({scope}) 需要用户确认", "ask"

def status():
    """返回完整状态摘要"""
    m = get()
    perms = get_permissions()
    profile = perms.get("profiles", {}).get(m.get("mode", "internal"), {})
    
    lines = [
        f"当前模式: {m.get('mode','?')} v{m.get('version',1)}",
        f"切换于: {m.get('switched_at','?')}",
        f"策略描述: {profile.get('description','无')}",
        f"允许: {', '.join(profile.get('allow',[]))}",
        f"拒绝: {', '.join(profile.get('deny',[]))}",
        f"询问: {', '.join(profile.get('ask',[]))}",
        f"默认: {profile.get('defaultMode','allowAll')}",
    ]
    return '\n'.join(lines)

if __name__ == "__main__":
    if "--set" in sys.argv:
        idx = sys.argv.index("--set")
        if idx + 1 < len(sys.argv):
            ok, msg = set_mode(sys.argv[idx + 1])
            print(f"{'✅' if ok else '❌'} {msg}")
    elif "--check" in sys.argv:
        idx = sys.argv.index("--check")
        if idx + 1 < len(sys.argv):
            ok, msg, action = check(sys.argv[idx + 1])
            print(f"{'✅' if ok else ('❓' if action == 'ask' else '❌')} {msg}")
    elif "--status" in sys.argv:
        init()
        print(status())
    else:
        init()
        m = get()
        print(f"模式: {m.get('mode','?')}")
