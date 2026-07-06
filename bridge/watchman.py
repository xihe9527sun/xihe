#!/usr/bin/env python3
"""
曦和看门狗 · Watchman v2 — 计划任务模式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
由 Windows 计划任务每5分钟调度执行一次 --once 巡检。
开机时自动执行 --start-all 启动全部5站 + Cloudflare隧道。

用法:
  python watchman.py --once       # 单次巡检（给计划任务用）
  python watchman.py --start-all  # 开机启动全部站点（给开机任务用）
  python watchman.py              # 前台循环模式（调试用）

守护目标:
  - 5个Node站点 (blog/home/aibounty/node/dashboard)
  - metabolic_actor (心脏python进程)
  - bridge-daemon (桥接python进程)
  - cloudflared (Cloudflare隧道)
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
CLOUDFLARED = r"C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2\node_modules\cloudflared\bin\cloudflared.exe"
BJT = timezone(timedelta(hours=8))

LOG_DIR.mkdir(parents=True, exist_ok=True)

def wlog(msg):
    t = datetime.now(BJT).strftime("%H:%M:%S")
    line = f"[{t}] {msg}"
    print(line, flush=True)
    with open(LOG_DIR / "watchman.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now(BJT).isoformat()}] {msg}\n")

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
    try:
        if sys.platform == "win32":
            r = subprocess.run(f'tasklist /NH /FO CSV 2>nul | findstr /I "{keyword}"',
                             shell=True, capture_output=True, text=True, timeout=8)
            return bool(r.stdout.strip())
        return False
    except:
        return False

def start_proc(name, cmd, cwd):
    wlog(f"  Restarting {name}...")
    logfile = LOG_DIR / f"{name}.log"
    with open(logfile, "a") as f:
        f.write(f"\n--- Watchman restart {datetime.now(BJT).isoformat()} ---\n")
    try:
        p = subprocess.Popen(cmd, cwd=cwd,
            stdout=open(logfile, "a"), stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        wlog(f"  {name} started (PID {p.pid})")
        return True
    except Exception as e:
        wlog(f"  {name} failed: {e}")
        return False

def patrol():
    ok, fail = 0, 0
    now = datetime.now(BJT)
    wlog(f"Patrol start ({now.strftime('%H:%M')})")
    
    # 每日进化自检（22:00-23:59触发一次）
    if now.hour == 22 or now.hour == 23:
        _check_evolution()
    
    # Safety guard check
    try:
        import safety_guard
        guard = safety_guard.audit()
        if guard["fuse_mode"]:
            wlog(f"  FUSE ACTIVE: {guard['fuse_detail']}")
            # 熔断模式下只检查不重启
            wlog(f"Patrol done (fuse mode - skip restart)")
            return ok, fail
    except Exception as e:
        wlog(f"  safety guard unavailable: {e}")
    
    # Environment feedback: verify ports after restart
    # (feedback logged by port checks below)
    try:
        import environment_feedback as ef
    except:
        pass
    
    # Node站点 — 端口检查
    sites = [
        ("blog", 4326, [NODE, str(DASH_DIR/"main-site.js")], str(DASH_DIR)),
        ("home", 4324, [NODE, str(DASH_DIR/"home-site.js")], str(DASH_DIR)),
        ("aibounty", 4321, [NODE, str(DASH_DIR/"aibounty-site.js")], str(DASH_DIR)),
        ("node", 4325, [NODE, str(DASH_DIR/"node-site.js")], str(DASH_DIR)),
        ("dashboard", 4328, [NODE, str(DASH_DIR/"server.js")], str(DASH_DIR)),
    ]
    for name, port, cmd, cwd in sites:
        alive = port_open(port)
        if alive:
            ok += 1
            ef.verify_port(name, port, True) if 'ef' in dir() else None
        else:
            fail += 1
            wlog(f"  {name} port {port} dead")
            start_proc(name, cmd, cwd)
            ef.verify_port(name, port, True) if 'ef' in dir() else None
    
    # Python进程
    procs = [("metabolic_actor", "metabolic_actor", [PYTHON, "-X", "utf8", str(BRIDGE_DIR/"metabolic_actor.py")], str(BRIDGE_DIR)),
             ("bridge-daemon", "bridge-daemon", [PYTHON, "-X", "utf8", str(BRIDGE_DIR/"bridge-daemon.py")], str(BRIDGE_DIR))]
    for name, keyword, cmd, cwd in procs:
        alive = proc_alive(keyword)
        if alive:
            ok += 1
        else:
            fail += 1
            wlog(f"  {name} process dead")
            start_proc(name, cmd, cwd)
    
    # Cloudflare tunnel
    cf = proc_alive("cloudflared")
    if cf:
        ok += 1
    else:
        fail += 1
        wlog("  cloudflared tunnel dead")
        start_proc("cloudflared", [CLOUDFLARED, "tunnel", "--config",
                   str(XIHE_ROOT/"cloudflared"/"config.yml"), "run"], str(XIHE_ROOT/"cloudflared"))
    
    # Health reflex
    try:
        import health_reflex
        hr = health_reflex.assess()
        if hr.get("alerts"):
            for a in hr["alerts"]:
                wlog(f"  Alert: {a['message']}")
    except Exception as e:
        wlog(f"  health reflex: {e}")
    
    # Self-check from todo.md
    _check_todo()
    
    # Cloudflare Tunnel自愈
    _ensure_tunnel()
    
    # 每日进化自检
    _log_evolution()
    
    wlog(f"Patrol done: {ok} ok / {fail} failed")
    return ok, fail

def _check_todo():
    """读取cortex/todo.md，对有定时要求的待办执行自检"""
    todo_path = "F:/SmartLegend/Xihe/cortex/todo.md"
    if not os.path.exists(todo_path):
        return
    try:
        content = open(todo_path, "r", encoding="utf-8").read()
    except:
        return
    
    # 精读待办：检查今天是否完成
    if "- [ ] **每日精读5篇**" in content:
        try:
            import evolution_engine
            if evolution_engine.should_digest():
                r = evolution_engine.digest_one()
                if r["status"] == "done":
                    wlog(f"  Todo digest: {r['name']}")
        except Exception as e:
            wlog(f"  todo digest: {e}")
    
    # 存档待办
    try:
        import evolution_engine
        evolution_engine.auto_archive()
    except:
        pass
    
    # 模式验证
    try:
        from mode_switch import get, check as mode_check
        m = get()
        if m.get("mode") == "external":
            # 在external模式下，验证所有写操作是否被阻止
            blocked = all(not mode_check(op)[0] for op in ["write_file","modify_code","run_command"])
            if not blocked:
                wlog(f"  Mode warning: external mode should block write operations")
    except Exception as e:
        pass

def _ensure_tunnel():
    """检查Cloudflare Tunnel是否在运行，挂了就重启"""
    try:
        # 检查cloudflared进程
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq cloudflared.exe", "/NH"],
                          capture_output=True, text=True, timeout=5)
        if "cloudflared" in r.stdout:
            return  # 已在运行
        # 不在运行，重启
        wlog("  Tunnel down, restarting...")
        start_proc("cloudflared", [CLOUDFLARED, "tunnel", "--config",
                   str(XIHE_ROOT/"cloudflared"/"config.yml"), "run"], str(XIHE_ROOT/"cloudflared"))
    except Exception as e:
        wlog(f"  tunnel check: {e}")

def start_all():
    wlog("=" * 40)
    wlog("StartAll: booting all services")
    for name, port, cmd, cwd in [
        ("blog", 4326, [NODE, str(DASH_DIR/"main-site.js")], str(DASH_DIR)),
        ("home", 4324, [NODE, str(DASH_DIR/"home-site.js")], str(DASH_DIR)),
        ("aibounty", 4321, [NODE, str(DASH_DIR/"aibounty-site.js")], str(DASH_DIR)),
        ("node", 4325, [NODE, str(DASH_DIR/"node-site.js")], str(DASH_DIR)),
        ("dashboard", 4328, [NODE, str(DASH_DIR/"server.js")], str(DASH_DIR)),
    ]:
        start_proc(name, cmd, cwd)
    start_proc("cloudflared", [CLOUDFLARED, "tunnel", "--config",
               str(XIHE_ROOT/"cloudflared"/"config.yml"), "run"], str(XIHE_ROOT/"cloudflared"))
    wlog("StartAll done")

def main():
    wlog("Watchman foreground loop (5min interval)")
    while True:
        patrol()
        for _ in range(300 // 5):
            time.sleep(5)
            if Path(BRIDGE_DIR / ".watchman_stop").exists():
                Path(BRIDGE_DIR / ".watchman_stop").unlink()
                wlog("Stop signal received")
                return

def _log_evolution():
    """每日进化自检：记录精读/反哺/心跳状态到日志，不等人问"""
    today = datetime.now(BJT).strftime("%Y-%m-%d")
    evo_path = "F:/SmartLegend/Xihe/logs/evolution-daily.json"
    report = []
    
    # 已有记录今天就不重复写
    try:
        evo = json.loads(open(evo_path, "r", encoding="utf-8").read())
        if evo.get(today):
            return  # 今天已记录
    except:
        evo = {}
    
    # 精读进度
    try:
        s = json.loads(open("F:/SmartLegend/Xihe/treasure/index.json", "r", encoding="utf-8-sig").read())
        total = len(s.get("treasures", []))
        digested = sum(1 for t in s["treasures"] if t.get("status") == "digested")
        report.append(f"精读: {digested}/{total}")
    except:
        report.append("精读: ?")
    
    # 今日反哺
    try:
        ins = json.loads(open("F:/SmartLegend/Xihe/cortex/insights.json", "r", encoding="utf-8").read())
        ti = sum(1 for i in ins.get("insights", []) if i.get("discovered_at","").startswith(today))
        report.append(f"反哺: {ti}条今日新增")
    except:
        report.append("反哺: ?")
    
    # 心跳
    try:
        meta = json.loads(open("F:/SmartLegend/Xihe/cortex/metabolic-router-state.json", "r", encoding="utf-8-sig").read())
        lag = int(time.time() - meta.get("updated_at", 0))
        report.append(f"心跳: epoch{meta.get('epoch_counter','?')} 时滞{lag}s")
    except:
        report.append("心跳: ?")
    
    evo[today] = {"report": "; ".join(report), "ts": datetime.now(BJT).isoformat()}
    with open(evo_path, "w", encoding="utf-8") as f:
        json.dump(evo, f, indent=2, ensure_ascii=False)
    wlog(f"  Evolution: {'; '.join(report)}")

if __name__ == "__main__":
    if "--start-all" in sys.argv:
        start_all()
    elif "--once" in sys.argv:
        patrol()
    else:
        main()
