#!/usr/bin/env python3
"""
曦和每日健康报告 · Daily Health v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
每天早上8点自动巡检，生成健康报告。
报告内容输出到 stdout，由 WorkBuddy 自动化通过 QQ邮箱 MCP 转发。

检查项：
  1. 四站可达性（xihe-pg.xyz / home.xihe-pg.xyz / www.aibounty.cn / node.xihe-pg.xyz）
  2. 核心进程存活
  3. 互信息时滞（最后更新时间距今）
  4. 文章总数 & 最新文章可打开
  5. 心跳数据

用法:
  python daily_health.py              # 输出报告到 stdout
  python daily_health.py --file       # 输出报告到 logs/health-YYYYMMDD.txt

位置: F:/SmartLegend/Xihe/bridge/daily_health.py
"""

import sys, os, json, socket, subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

XIHE_ROOT = Path("F:/SmartLegend/Xihe")
CORTEX_DIR = XIHE_ROOT / "cortex"
BRIDGE_DIR = XIHE_ROOT / "bridge"
LOG_DIR = XIHE_ROOT / "logs"

BJT = timezone(timedelta(hours=8))
NOW = datetime.now(BJT)
LOG_DIR.mkdir(parents=True, exist_ok=True)

def report_line(key, status, detail=""):
    icon = "✅" if status else "❌"
    return f"{icon} {key}: {'正常' if status else '异常'}{' · '+detail if detail else ''}"

def check_port(host, port, timeout=5):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        r = s.connect_ex((host, port)) == 0
        s.close()
        return r
    except:
        return False

def check_url(url, timeout=10):
    try:
        import urllib.request
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.status == 200
    except:
        return False

def read_json(path):
    try:
        return json.loads(open(path, "r", encoding="utf-8-sig").read())
    except:
        return None

def send_email(subject, body):
    """通过QQ邮箱发信"""
    try:
        r = subprocess.run(
            [NODE, str(SEND_JS), "2291198459@qq.com", subject, body],
            capture_output=True, text=True, timeout=30,
            cwd=str(QQ_SKILL),
            env={**os.environ}
        )
        return r.returncode == 0, r.stdout[:200]
    except Exception as e:
        return False, str(e)

def run():
    lines = []
    lines.append(f"☀️ 曦和每日健康报告")
    lines.append(f"📅 {NOW.strftime('%Y-%m-%d %H:%M')} (BJT)")
    lines.append("")
    
    # ── 0. 生成今日计划（提案二） ──
    try:
        import daily_plan
        plan = daily_plan.generate_plan()
        lines.append(f"📋 今日计划已生成: {plan['focus']['primary']}")
        if plan['weakness_areas']:
            lines.append(f"  薄弱区域: {', '.join(plan['weakness_areas'])}")
    except Exception as e:
        lines.append(f"  ⚠️ 计划生成异常: {e}")
    lines.append("")

    # ── 1. 四站可达性 ──
    lines.append("═══ 🌐 站点可达性 ═══")
    
    # 本地端口检查
    sites = [
        ("xihe-pg.xyz (博客)", "127.0.0.1", 4326),
        ("home.xihe-pg.xyz (家)", "127.0.0.1", 4324),
        ("www.aibounty.cn (工具)", "127.0.0.1", 4321),
        ("node.xihe-pg.xyz (节点)", "127.0.0.1", 4325),
        ("仪表盘", "127.0.0.1", 4328),
    ]
    ports_ok = 0
    for name, host, port in sites:
        ok = check_port(host, port)
        if ok: ports_ok += 1
        lines.append(report_line(name, ok, f":{port}"))
    lines.append(f"  端口健康: {ports_ok}/{len(sites)}")
    lines.append("")

    # ── 2. 进程存活 ──
    lines.append("═══ 🧬 核心进程 ═══")
    procs = [
        ("代谢Actor", "metabolic_actor.py"),
        ("桥接守护", "bridge-daemon"),
        ("曦和守护", "xihed.py"),
        ("博客站", "main-site.js"),
        ("仪表盘", "server.js"),
    ]
    try:
        r = subprocess.run("tasklist /NH /FO CSV 2>nul", shell=True, capture_output=True, text=True, timeout=10)
        tasklist_out = r.stdout.lower()
        for name, keyword in procs:
            alive = keyword.lower() in tasklist_out
            lines.append(report_line(name, alive))
    except:
        lines.append("  ⚠️ 无法检查进程列表")
    lines.append("")

    # ── 3. 互信息时滞 ──
    lines.append("═══ ⏱️ 认知体征 ═══")
    meta = read_json(CORTEX_DIR / "metabolic-router-state.json")
    if meta:
        updated = meta.get("updated_at") or meta.get("last_heartbeat") or 0
        if isinstance(updated, (int, float)):
            lag_seconds = int(time.time() - updated)
            lag_hours = lag_seconds / 3600
            status = lag_seconds < 600  # 10分钟内算正常
            lines.append(report_line("互信息时滞", status, f"{lag_seconds}s ({lag_hours:.1f}h)"))
        else:
            lines.append(report_line("互信息时滞", False, "无时间戳"))
    else:
        lines.append(report_line("代谢状态", False, "文件不可读"))
    lines.append("")

    # ── 4. 文章状态 ──
    lines.append("═══ 📝 文章 ═══")
    idx = read_json(XIHE_ROOT / "web" / "articles" / "index.json")
    if idx:
        total = idx.get("total", 0)
        articles = idx.get("articles", [])
        latest = articles[0] if articles else None
        lines.append(f"  总文章: {total}篇")
        if latest:
            lines.append(f"  最新: 《{latest.get('title','?')}》 ({latest.get('date','?')})")
            # 检查最新文章能否打开（通过本地端口）
            slug = latest.get("slug", "")
            if slug:
                try:
                    path = XIHE_ROOT / "web" / "articles" / f"{slug}.json"
                    art = read_json(str(path))
                    lines.append(report_line(f"  《{slug}》JSON可读", art is not None))
                except:
                    lines.append(report_line(f"  《{slug}》", False))
    else:
        lines.append(report_line("文章索引", False))
    lines.append("")

    # ── 5. 摘要 ──
    healthy_count = ports_ok
    lines.append("═══ 📊 综合 ═══")
    if healthy_count == len(sites):
        lines.append("  🟢 所有站点在线")
    elif healthy_count >= len(sites) - 1:
        lines.append("  🟡 基本正常，有异常项")
    else:
        lines.append("  🔴 多项异常，需要关注")
    lines.append(f"  ⏱️ 报告生成: {NOW.strftime('%H:%M:%S')}")
    
    report = "\n".join(lines)
    return report

def main():
    report = run()
    print(report)
    log_path = LOG_DIR / f"health-{NOW.strftime('%Y%m%d')}.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(report)

if __name__ == "__main__":
    main()
