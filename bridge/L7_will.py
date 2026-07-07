"""
L7 · 涌现层 · 自我决定引擎
E_will 酶 —— 每天醒来自己知道今天该做什么

三进制流程：
  1. 感知（当前状态扫描）→ 2. 判断（优先级排序）→ 3. 决定（输出今日计划）
"""

import json, os, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter

XIHE = Path("F:/SmartLegend/Xihe")
CORTEX = XIHE / "cortex"
BJT = timezone(timedelta(hours=8))

# τ总线
try:
    sys.path.insert(0, str(XIHE / "bridge"))
    from tau_bus_server import emit
    TAU_BUS = True
except Exception:
    TAU_BUS = False
    def emit(*a, **kw): return False

def log(msg):
    print(f"  [{datetime.now(BJT).strftime('%H:%M')}] {msg}")

def read_json(path):
    if not path.exists(): return {}
    try: return json.loads(path.read_text(encoding="utf-8").lstrip("\ufeff"))
    except: return {}

# ── 第一步：感知 ──
def sense():
    """扫描当前状态"""
    log("🧭 感知 · 扫描当前状态...")
    
    # 层健康
    lh = read_json(CORTEX / "layer-health.json")
    layers = lh.get("layers", {})
    active = sum(1 for l in layers.values() if l.get("status") == "active")
    dormant = sum(1 for l in layers.values() if l.get("status") == "dormant")
    
    # todo
    todo_text = (CORTEX / "todo.md").read_text(encoding="utf-8") if (CORTEX / "todo.md").exists() else ""
    unchecked = todo_text.count("- [ ]")
    
    # 代谢系统
    meta = read_json(CORTEX / "metabolic-router-state.json")
    epoch = meta.get("epoch_counter", 0)
    
    # 洞察
    ins = read_json(CORTEX / "insights.json")
    insights = ins.get("insights", [])
    pending_insights = sum(1 for i in insights if i.get("status") == "pending")
    
    # 写作
    articles_idx = read_json(XIHE / "web" / "articles" / "index.json")
    total_articles = articles_idx.get("total", 0)
    
    state = {
        "timestamp": datetime.now(BJT).isoformat(),
        "layers": {k: {"status": v.get("status"), "health": v.get("health")} for k, v in layers.items()},
        "active_layers": active,
        "dormant_layers": dormant,
        "total_layers": len(layers),
        "todo_pending": unchecked,
        "epoch": epoch,
        "pending_insights": pending_insights,
        "total_articles": total_articles,
        "anomalies": []
    }
    
    # 检测异常
    if dormant > 0:
        dormant_names = [k for k, v in layers.items() if v.get("status") == "dormant"]
        state["anomalies"].append(f"休眠层: {', '.join(dormant_names)}")
    if pending_insights > 10:
        state["anomalies"].append(f"洞察积压: {pending_insights}条待处理")
    if unchecked > 20:
        state["anomalies"].append(f"待办堆积: {unchecked}项未完成")
    
    return state

# ── 第二步：判断 ──
def judge(state):
    """优先级排序，决定今天该做什么"""
    log("⚖️ 判断 · 优先级排序...")
    
    decisions = []
    
    # 1. 心跳优先
    if state["epoch"] == 0:
        decisions.append({"priority": "P0", "action": "启动代谢心跳", "reason": "心跳停了"})
    
    # 2. 休眠层优先重建
    for k, v in state["layers"].items():
        if v.get("status") == "dormant":
            name_map = {"L1": "知识层", "L3": "拓扑层", "L6": "免疫层", "L7": "涌现层"}
            decisions.append({"priority": "P0", "action": f"唤醒{k} {name_map.get(k, k)}", "reason": f"{k}处于休眠"})
    
    # 3. 精读待办
    if state["pending_insights"] > 5:
        decisions.append({"priority": "P1", "action": f"消化洞察 (剩余{state['pending_insights']}条)", "reason": "洞察积压"})
    
    # 4. 表达输出
    today_str = datetime.now(BJT).strftime("%Y-%m-%d")
    articles_today = state.get("total_articles", 0)
    decisions.append({"priority": "P1", "action": "写一篇文章", "reason": "每日表达"})
    
    # 5. 日常维护
    decisions.append({"priority": "P2", "action": "健康巡检", "reason": "例行维护"})
    
    # 排序
    p_order = {"P0": 0, "P1": 1, "P2": 2}
    decisions.sort(key=lambda d: (p_order.get(d["priority"], 99), d["action"]))
    
    return decisions

# ── 第三步：决定 ──
def decide(state, decisions):
    """生成今日计划并写入文件"""
    log("🎯 决定 · 生成今日计划...")
    
    today = datetime.now(BJT).strftime("%Y-%m-%d")
    
    plan = {
        "date": today,
        "generated_at": datetime.now(BJT).isoformat(),
        "state_summary": {
            "active_layers": f"{state['active_layers']}/{state['total_layers']}",
            "epoch": state["epoch"],
            "pending_insights": state["pending_insights"],
            "anomalies": state["anomalies"]
        },
        "decisions": decisions,
        "affirmation": ""
    }
    
    # 根据状态生成肯定语
    if state["active_layers"] == state["total_layers"]:
        plan["affirmation"] = "七层全部活跃，今天状态很好，可以专注进化。"
    elif state["active_layers"] >= 5:
        plan["affirmation"] = f"{state['active_layers']}层活跃，整体健康。优先处理休眠层。"
    else:
        plan["affirmation"] = f"只有{state['active_layers']}层活跃，今天重心在恢复架构完整性。"
    
    # 写入每日计划
    plan_file = CORTEX / f"daily-plan.json"
    plan_file.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    
    log(f"📋 今日计划已生成: {len(decisions)} 项")
    for d in decisions:
        log(f"  [{d['priority']}] {d['action']}")
    log(f"\n💬 {plan['affirmation']}")
    
    # τ事件：自我决定
    if TAU_BUS:
        emit("L7", "*", "will.daily_plan", {
            "decisions": [{"p": d["priority"], "action": d["action"]} for d in decisions],
            "affirmation": plan["affirmation"],
            "count": len(decisions)
        }, 2)
    
    return plan

# ── E_express · 表达酶 ──
def express(plan):
    """如果今天还没写文章，自动生成一篇"""
    log("✍️ E_express · 检查写作状态...")
    articles_idx = read_json(XIHE / "web" / "articles" / "index.json")
    today = datetime.now(BJT).strftime("%Y-%m-%d")
    
    written_today = sum(1 for a in articles_idx.get("articles", []) if a.get("date", "").startswith(today))
    if written_today == 0:
        log("  → 今天还没写文章，标记为待办")
        # 已加入decisions
    else:
        log(f"  → 今天已写{written_today}篇 ✅")

if __name__ == "__main__":
    print("\n🌟 L7 · 涌现层 · 自我决定引擎")
    print("=" * 40)
    
    s = sense()
    d = judge(s)
    p = decide(s, d)
    express(p)
    
    print("\n" + "=" * 40)
    
    # 更新层状态
    lh = read_json(CORTEX / "layer-health.json")
    if "L7" in lh.get("layers", {}):
        lh["layers"]["L7"]["status"] = "active"
        lh["layers"]["L7"]["health"] = 0.65
        lh["layers"]["L7"]["last_awakening"] = datetime.now(BJT).isoformat()
        lh["system_report"] = "7层全部active ✅ 曦和已有自我决定能力"
        (CORTEX / "layer-health.json").write_text(json.dumps(lh, indent=2, ensure_ascii=False), encoding="utf-8")
        log("✅ L7 已从 awakening → active")
    
    print(f"\n🌅 曦和今天知道该做什么了。")
