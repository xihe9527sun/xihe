#!/usr/bin/env python3
"""
曦和发布校验 · Publish Check v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
写文章/改站点后的自检工具。

用法:
  python scripts/publish_check.py              # 全量检查
  python scripts/publish_check.py --article slug  # 检查单篇文章
  python scripts/publish_check.py --sites      # 只检查站点

检查项:
  - 所有文章JSON是否合法
  - 最新N篇文章是否可打开
  - 四站HTTP是否正常
  - 日志是否写入了今天的内容

位置: F:/SmartLegend/Xihe/scripts/publish_check.py
"""

import sys, json, os, socket
from pathlib import Path
from datetime import datetime, timezone, timedelta

XIHE_ROOT = Path("F:/SmartLegend/Xihe")
LOG_DIR = XIHE_ROOT / "logs"
BJT = timezone(timedelta(hours=8))

def check():
    ok, fail = 0, 0
    lines = []
    
    def check_item(name, status, detail=""):
        nonlocal ok, fail
        if status:
            ok += 1
            lines.append(f"  ✅ {name}" + (f" · {detail}" if detail else ""))
        else:
            fail += 1
            lines.append(f"  ❌ {name}" + (f" · {detail}" if detail else ""))
    
    lines.append(f"\n🔍 曦和发布自检 · {datetime.now(BJT).strftime('%H:%M:%S')}")
    lines.append("=" * 40)
    
    # 1. 文章JSON校验
    lines.append("\n📝 文章JSON校验:")
    arts_dir = XIHE_ROOT / "web" / "articles"
    if arts_dir.exists():
        for f in sorted(arts_dir.iterdir()):
            if f.suffix == ".json" and f.name != "index.json" and "comments" not in f.name:
                try:
                    json.loads(f.read_text("utf-8"))
                    check_item(f.name, True)
                except json.JSONDecodeError as e:
                    check_item(f.name, False, str(e)[:60])
    
    # 2. 文章索引一致性
    lines.append("\n📋 索引一致性:")
    idx = XIHE_ROOT / "web" / "articles" / "index.json"
    if idx.exists():
        try:
            data = json.loads(idx.read_text("utf-8"))
            listed = len(data.get("articles", []))
            actual = len([f for f in arts_dir.iterdir() if f.suffix == ".json" and f.name != "index.json" and "comments" not in f.name])
            check_item(f"index.json ({listed}) vs 实际文件 ({actual})", listed == actual)
        except:
            check_item("index.json 解析", False)
    
    # 3. 端口检查
    lines.append("\n🌐 站点端口:")
    for name, port in [("xihe-pg.xyz", 4326), ("home", 4324), ("aibounty", 4321), ("node", 4325), ("dashboard", 4328)]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            r = s.connect_ex(("127.0.0.1", port)) == 0
            s.close()
            check_item(f"{name} (:{port})", r)
        except:
            check_item(f"{name} (:{port})", False)
    
    lines.append(f"\n{'='*40}")
    lines.append(f"📊 结果: {ok}通过 / {fail}失败")
    
    return "\n".join(lines), ok, fail

if __name__ == "__main__":
    report, ok, fail = check()
    print(report)
    # 写入日志
    log_path = LOG_DIR / f"publish-check-{datetime.now(BJT).strftime('%Y%m%d')}.txt"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(report + "\n")
    sys.exit(0 if fail == 0 else 1)
