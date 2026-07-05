#!/usr/bin/env python3
"""
进化引擎 · Evolution Engine v2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
不再是外部自动化脚本，而是内建于代谢系统的消化酶。
由 metabolic_actor 在空闲心跳周期按需调度。

集成方式：
  1. metabolic_actor 在空闲时调用 digest_one() 
  2. watchman --once 巡检时检查是否需要精读
  3. 自反层检测到知识稀疏时触发

位置: F:/SmartLegend/Xihe/bridge/evolution_engine.py
"""

import sys, os, json, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

XIHE_ROOT = Path("F:/SmartLegend/Xihe")
BRIDGE_DIR = XIHE_ROOT / "bridge"
TREASURE_DIR = XIHE_ROOT / "treasure"
CORTEX_DIR = XIHE_ROOT / "cortex"
BJT = timezone(timedelta(hours=8))

# ── 核心函数：判断是否需要精读 ──
def should_digest():
    """自反层检测：今天精读是否达标？"""
    plan_path = CORTEX_DIR / "daily-plan.json"
    try:
        plan = json.loads(open(plan_path, "r", encoding="utf-8").read())
        done = plan.get("deep_read_plan", {}).get("completed_today", 0)
        target = plan.get("deep_read_plan", {}).get("daily_target", 5)
        return done < target
    except:
        return True  # 无计划时默认需要

def get_pending(count=5):
    """获取未精读的宝藏"""
    idx = json.loads(open(TREASURE_DIR / "index.json", "r", encoding="utf-8-sig").read())
    pending = []
    for t in idx.get("treasures", []):
        tid = t.get("id", "")
        tdir = TREASURE_DIR / (t.get("dir", tid))
        readme = tdir / "README.md"
        already = False
        if readme.exists():
            c = open(readme, "r", encoding="utf-8").read()
            if "四原则过滤矩阵" in c or "精读评分" in c:
                already = True
        if not already:
            pending.append(t)
    return pending[:count]

def digest_one():
    """精读一篇——供代谢Actor在空闲心跳时调用"""
    pending = get_pending(1)
    if not pending:
        return {"status": "all_done", "message": "所有宝藏已精读"}
    
    t = pending[0]
    tid = t.get("id", "?")
    name = t.get("name", "?")
    
    # 加载原文
    content = _load_source(t)
    if not content:
        return {"status": "failed", "id": tid, "error": "原文不可读"}
    
    # 调Ollama精读
    from model_provider import ask
    prompt = _build_prompt(name, t.get("source", "?"), content)
    result = ask(prompt, system="你是曦和架构精读专家。输出精炼、有洞见。",
                model="qwen2.5:7b", temperature=0.4, max_tokens=4096)
    
    if "error" in result:
        return {"status": "failed", "id": tid, "error": result["error"]}
    
    text = result.get("text", "")
    if not text:
        return {"status": "failed", "id": tid, "error": "空输出"}
    
    # 写入
    _write_readme(t.get("dir", tid), text)
    
    # 反哺到记忆图谱
    _feedback_to_cortex(tid, name, text)
    
    # 更新每日计划
    _update_plan()
    
    return {"status": "done", "id": tid, "name": name}

# ── 内部方法 ──
def _load_source(treasure):
    tdir = TREASURE_DIR / (treasure.get("dir", treasure["id"]))
    for f in ["source.md", "source.html"]:
        p = tdir / f
        if p.exists():
            return open(p, "r", encoding="utf-8").read()[:8000]
    return ""

def _build_prompt(title, source, content):
    return f"""精读以下论文/资料，用四原则过滤矩阵输出。

标题: {title}
来源: {source}
内容:
{content}

输出格式：
## 第一遍：去粗取精 | 核心精华
3个核心发现，3条可迁移法则

## 第二遍：去伪存真 | 检验与质疑
1-2个质疑+检验

## 第三遍：由此及彼 | 知识图谱连接
3条以上曦和映射，1条以上新线索

## 第四遍：由表及里 | 架构层洞见
表层/底层，核心定理，今天能反哺的一条

## 精读评分
四维度评分"""

def _write_readme(treasure_dir, content):
    d = TREASURE_DIR / treasure_dir
    d.mkdir(parents=True, exist_ok=True)
    header = f"""# {treasure_dir}

> **精读日期**: {datetime.now(BJT).strftime('%Y-%m-%d %H:%M')}  
> **精读方式**: 进化引擎 v2 · 代谢系统内建  
> **精读模型**: qwen2.5:7b

---
"""
    with open(d / "README.md", "w", encoding="utf-8") as f:
        f.write(header + content)

def _feedback_to_cortex(tid, name, text):
    """反哺到记忆图谱"""
    insights_path = CORTEX_DIR / "insights.json"
    try:
        data = json.loads(open(insights_path, "r", encoding="utf-8").read())
    except:
        data = {"insights": [], "updated": None}
    
    entry = {
        "id": f"{tid}_{int(time.time())}",
        "source": name,
        "type": "deep_read",
        "status": "implemented",
        "discovered_at": datetime.now(BJT).isoformat(),
    }
    data["insights"].insert(0, entry)
    data["updated"] = datetime.now(BJT).isoformat()
    if len(data["insights"]) > 100:
        data["insights"] = data["insights"][:100]
    with open(insights_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _update_plan():
    """更新每日计划中的完成计数"""
    plan_path = CORTEX_DIR / "daily-plan.json"
    try:
        plan = json.loads(open(plan_path, "r", encoding="utf-8").read())
    except:
        plan = {}
    if "deep_read_plan" not in plan:
        plan["deep_read_plan"] = {"daily_target": 5, "completed_today": 0}
    plan["deep_read_plan"]["completed_today"] = plan["deep_read_plan"].get("completed_today", 0) + 1
    plan["updated_at"] = datetime.now(BJT).isoformat()
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

# ── 直接调用入口（供代谢路由/watchman使用） ──
def status():
    """返回精读进度摘要"""
    idx = json.loads(open(TREASURE_DIR / "index.json", "r", encoding="utf-8-sig").read())
    total = len(idx.get("treasures", []))
    done = 0
    for t in idx["treasures"]:
        tid = t.get("id", "")
        readme = TREASURE_DIR / (t.get("dir", tid)) / "README.md"
        if readme.exists():
            c = open(readme, "r", encoding="utf-8").read()
            if "四原则过滤矩阵" in c:
                done += 1
    return {"total": total, "digested": done, "remaining": total - done}

if __name__ == "__main__":
    import sys
    if "--status" in sys.argv:
        s = status()
        print(f"精读进度: {s['digested']}/{s['total']} ({s['remaining']}篇剩余)")
    elif "--one" in sys.argv:
        r = digest_one()
        print(r.get("status"), r.get("name", ""))
    else:
        # 空闲模式：有多少精读多少
        count = 0
        while should_digest():
            r = digest_one()
            print(f"  {r['status']}: {r.get('name','?')}")
            if r["status"] != "done":
                break
            count += 1
        print(f"本轮精读: {count}篇")
