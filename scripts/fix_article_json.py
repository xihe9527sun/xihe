#!/usr/bin/env python3
"""
文章JSON引号自动修复脚本
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
每次写入文章JSON时自动处理正文中的中文引号，
避免JSON解析失败导致"文章未找到"。

用法：
  python fix_article_json.py                    # 检查所有文章
  python fix_article_json.py --slug <slug>       # 修复指定文章
  python fix_article_json.py --watch             # 监控模式

位置: F:/SmartLegend/Xihe/scripts/fix_article_json.py
"""

import json, os, re, sys, time
from pathlib import Path

ARTICLES_DIR = Path("F:/SmartLegend/Xihe/web/articles")

def fix_file(fp):
    """修复单篇文章JSON文件中的引号问题"""
    try:
        raw = open(fp, "r", encoding="utf-8").read()
    except:
        return False, "不可读"
    
    # 尝试解析
    try:
        json.loads(raw)
        return True, "无需修复"
    except json.JSONDecodeError as e:
        pass
    
    # 修复策略：找到body字段的值，替换其中的裸引号为中文引号
    fixed = raw
    # 策略1: 中文语境下的双引号 -> 「」
    fixed = re.sub(r'(?<=[\u4e00-\u9fff])"(?=[\u4e00-\u9fff])', '「', fixed)
    fixed = re.sub(r'(?<=[\u4e00-\u9fff])"(?=[\u4e00-\u9fff\w])', '」', fixed)
    fixed = re.sub(r'(?<=[\u4e00-\u9fff\w。])"(?=[\u4e00-\u9fff\w])', '「', fixed)
    fixed = re.sub(r'(?<=[\u4e00-\u9fff\w])"(?=[\u4e00-\u9fff\w。])', '」', fixed)
    
    # 策略2: 剩余裸引号 -> 转义
    # （在body字符串内部的引号）
    try:
        json.loads(fixed)
        open(fp, "w", encoding="utf-8").write(fixed)
        return True, "已修复中文引号"
    except json.JSONDecodeError:
        return False, "修复后仍然无效"

def scan_all():
    """扫描并修复所有文章"""
    files = sorted(ARTICLES_DIR.glob("*.json"))
    ok, fixed, failed = 0, 0, 0
    for fp in files:
        if fp.name == "index.json":
            continue
        succ, msg = fix_file(fp)
        if msg == "无需修复":
            ok += 1
        elif succ:
            fixed += 1
            print(f"  ✅ {fp.name}: {msg}")
        else:
            failed += 1
            print(f"  ❌ {fp.name}: {msg}")
    print(f"\n总计: {len(files)-1}篇, {ok}正常, {fixed}已修复, {failed}失败")
    return fixed > 0

if __name__ == "__main__":
    if "--slug" in sys.argv:
        idx = sys.argv.index("--slug")
        slug = sys.argv[idx+1]
        fp = ARTICLES_DIR / f"{slug}.json"
        if fp.exists():
            succ, msg = fix_file(fp)
            print(f"{'✅' if succ else '❌'} {slug}: {msg}")
        else:
            print(f"❌ {slug} 不存在")
    elif "--watch" in sys.argv:
        print("监控模式：每30秒检查新文章...")
        from datetime import datetime
        checked = set()
        while True:
            for fp in sorted(ARTICLES_DIR.glob("*.json")):
                if fp.name == "index.json" or fp.name in checked:
                    continue
                succ, msg = fix_file(fp)
                if msg != "无需修复":
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {fp.name}: {msg}")
                checked.add(fp.name)
            time.sleep(30)
    else:
        scan_all()
