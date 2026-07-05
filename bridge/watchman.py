#!/usr/bin/env python3
"""
曦和看门狗 · Watchman v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
每5分钟巡检核心进程，死了自动重启。
"""
import sys, os, time, subprocess, socket, json
from pathlib import Path
from datetime import datetime, timezone, timedelta

XIHE_ROOT = Path("F:/SmartLegend/Xihe")
DASH_DIR = XIHE_ROOT / "XiheDashboard"
BRIDGE_DIR = XIHE_ROOT / "bridge"
CORTEX_DIR = XIHE_ROOT / "cortex"
LOG_DIR = XIHE_ROOT / "logs"
PYTHON = r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"
NODE = r"C:\Users\Administrator\.workbuddy\binaries\node\versions\22.12.0\node.exe"
BJT = timezone(timedelta(hours=8))

LOG_DIR.mkdir(parents=True, exist_ok=True)
logfile = open(LOG_DIR / "watchman.log", "a", encoding="utf-8")

def wlog(msg):
    t = datetime.now(BJT).strftime("%H:%M:%S")
    line = f"[{t}] {msg}"
    print(line, flush=True)
    logfile.write(f"[{datetime.now(BJT).isoformat()}] {msg}\n")
    logfile.flush()

# ── 端口检查（比tasklist快） ──
PORT_MAP = {
    "blog":       {"port": 4326, "cmd": [NODE, str(DASH_DIR/"main-site.js")],    "cwd": str(DASH_DIR)},
    "home":       {"port": 4324, "cmd": [NODE, str(DASH_DIR/"home-site.js")],    "cwd": str(DASH_DIR)},
    "aibounty":   {"port": 4321, "cmd": [NODE, str(DASH_DIR/"aibounty-site.js")],"cwd": str(DASH_DIR)},
    "node":       {"port": 4325, "cmd": [NODE, str(DASH_DIR/"node-site.js")],    "cwd": str(DASH_DIR)},
    "dashboard":  {"port": 4328, "cmd": [NODE, str(DASH_DIR/"server.js")],      "cwd": str(DASH_DIR)},
}

# ── 进程名检查 ──
PROC_MAP = {
    "metabolic_actor": {"keyword": "metabolic_actor", "cmd": [PYTHON, "-X", "utf8", str(BRIDGE_DIR/"metabolic_actor.py")], "cwd": str(BRIDGE_DIR)},
    "bridge-daemon":   {"keyword": "bridge-daemon",   "cmd": [PYTHON, "-X", "utf8", str(BRIDGE_DIR/"bridge-daemon.py")], "cwd": str(BRIDGE_DIR)},
}

def port_open(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        r = s.connect_ex(("127.0.0.1", port)) == 0
        s.close()
        return r
    except:
        return False

def proc_alive(keyword):
    """检查进程是否存在（跨平台）"""
    try:
        if sys.platform == "win32":
            r = subprocess.run(f'tasklist /NH /FO CSV 2>nul | findstr /I "{keyword}"',
                             shell=True, capture_output=True, text=True, timeout=8)
            return bool(r.stdout.strip())
        else:
            r = subprocess.run(["pgrep", "-f", keyword], capture_output=True, text=True, timeout=5)
            return r.returncode == 0
    except:
        return False

def start_proc(name, cmd, cwd):
    wlog(f"  🔄 重启 {name}...")
    try:
        log_path = LOG_DIR / f"{name}.log"
        with open(log_path, "a") as f:
            f.write(f"\n--- Watchman restart {datetime.now(BJT).isoformat()} ---\n")
        p = subprocess.Popen(cmd, cwd=cwd,
            stdout=open(log_path, "a"), stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        wlog(f"  ✅ {name} 已启动 (PID {p.pid})")
        return True
    except Exception as e:
        wlog(f"  ❌ {name} 启动失败: {e}")
        return False

def patrol():
    """巡检一轮——同时触发健康自反回路"""
    ok, fail = 0, 0
    
    # 健康自反：写入脉冲 + 评估
    try:
        import health_reflex
        hr = health_reflex.assess()
        if hr.get("alerts"):
            for a in hr["alerts"]:
                wlog(f"  ⚠️ {a['message']}")
    except Exception as e:
        wlog(f"  ⚠️ 健康自反异常: {e}")
    
    # 端口巡检
    for name, info in PORT_MAP.items():
        alive = port_open(info["port"])
        if alive:
            ok += 1
        else:
            fail += 1
            wlog(f"  ❌ {name} (:{info['port']}) 端口不通")
            start_proc(name, info["cmd"], info["cwd"])
    
    # 进程巡检
    for name, info in PROC_MAP.items():
        alive = proc_alive(info["keyword"])
        if alive:
            ok += 1
        else:
            fail += 1
            wlog(f"  ❌ {name} 进程已死")
            start_proc(name, info["cmd"], info["cwd"])
    
    # Cloudflare隧道
    cf = proc_alive("cloudflared")
    if cf:
        ok += 1
    else:
        fail += 1
        wlog(f"  ❌ cloudflared 隧道已死")
    
    wlog(f"  📊 巡检完成: {ok}正常 / {fail}异常")
    return ok, fail

def main():
    wlog("=" * 40)
    wlog("👁️ Watchman 启动")
    
    if "--once" in sys.argv:
        wlog("🔍 单次巡检模式")
        patrol()
        wlog("👋 结束")
        return

    wlog(f"⏱️ 每{300}秒巡检一轮")
    
    # 首轮
    wlog("🔍 首轮巡检")
    patrol()
    
    while True:
        for _ in range(300 // 5):
            time.sleep(5)
        wlog("🔍 例行巡检")
        patrol()

if __name__ == "__main__":
    main()
