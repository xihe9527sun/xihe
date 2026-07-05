#!/usr/bin/env python3
"""
精读反哺管道 · Feedback to Cortex v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
每次精读完成后，自动将精读中发现的知识反馈回曦和自身：
  1. 新线索 → 写入 cortex/insights.json（可在会话中注入）
  2. 架构差距 → 写入明日计划（cortex/daily-plan.json 的 improvement_items）
  3. 精读评分 → 写入自反层输入（cortex/health-status.json 的 insights）

使精读产出自动流入认知体系，而不是停在 README.md 里落灰。

位置: F:/SmartLegend/Xihe/bridge/feedback_cortex.py
"""

import json, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

XIHE_ROOT = Path("F:/SmartLegend/Xihe")
CORTEX_DIR = XIHE_ROOT / "cortex"
BJT = timezone(timedelta(hours=8))
INSIGHTS_FILE = CORTEX_DIR / "insights.json"
MAX_INSIGHTS = 50

def load_insights():
    try:
        return json.loads(open(INSIGHTS_FILE, "r", encoding="utf-8").read())
    except:
        return {"insights": [], "updated": None}

def save_insights(data):
    CORTEX_DIR.mkdir(parents=True, exist_ok=True)
    with open(INSIGHTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def record_insight(treasure_id, treasure_name, insight_type, content, priority="P2"):
    """记录一条精读反哺洞察"""
    data = load_insights()
    entry = {
        "id": f"{treasure_id}_{int(time.time())}",
        "source": treasure_name,
        "type": insight_type,  # "connection" | "gap" | "architecture" | "practice"
        "content": content,
        "priority": priority,
        "discovered_at": datetime.now(BJT).isoformat(),
        "status": "pending",  # pending | in_plan | implemented
    }
    data["insights"].insert(0, entry)
    data["updated"] = datetime.now(BJT).isoformat()
    
    # 裁切
    if len(data["insights"]) > MAX_INSIGHTS:
        data["insights"] = data["insights"][:MAX_INSIGHTS]
    
    save_insights(data)
    return entry

def add_to_daily_plan(insight):
    """将洞察加入每日计划的 improvement_items"""
    plan_path = CORTEX_DIR / "daily-plan.json"
    try:
        plan = json.loads(open(plan_path, "r", encoding="utf-8").read())
    except:
        plan = {}
    
    if "improvement_items" not in plan:
        plan["improvement_items"] = []
    
    plan["improvement_items"].append({
        "source": insight["source"],
        "type": insight["type"],
        "content": insight["content"],
        "priority": insight["priority"],
        "discovered_at": insight["discovered_at"],
    })
    
    plan["updated_at"] = datetime.now(BJT).isoformat()
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

def auto_feedback(treasure_id, treasure_name, connections=None, gaps=None, architectures=None):
    """一键反哺：记录洞察 + 加入计划 + 返回总结"""
    results = []
    
    if connections:
        for c in connections:
            e = record_insight(treasure_id, treasure_name, "connection", c, "P2")
            results.append(e)
    
    if gaps:
        for g in gaps:
            e = record_insight(treasure_id, treasure_name, "gap", g, "P1")
            add_to_daily_plan(e)
            results.append(e)
    
    if architectures:
        for a in architectures:
            e = record_insight(treasure_id, treasure_name, "architecture", a, "P1")
            add_to_daily_plan(e)
            results.append(e)
    
    return results

if __name__ == "__main__":
    # 测试：把今天三篇精读的反哺一次性写入
    results = auto_feedback(
        "tau-scaling-v2-hetinbo",
        "τ缩微V2",
        connections=[
            "τ统一优化目标 → 代谢周期的时间粒度应可配置",
            "LogicFolding → 自动识别高频搭档酶对",
        ],
        gaps=[
            "酶对熔合目前靠人工判断，需要自动识别高频搭档",
        ],
    )
    results += auto_feedback(
        "sovra-cognitive-architecture",
        "自进化Agent综述",
        connections=[
            "四组件反馈回路 → 曦和缺'环境反馈'和'安全护栏'（已补）",
            "Memory-R1 → 记忆权重应主动优化而非被动存储",
        ],
        gaps=[
            "代谢路由traces只存不用，应定期用traces训练先验",
        ],
        architectures=[
            "精读流程本身应该自动反哺到超图，而不是手动搬运",
        ],
    )
    results += auto_feedback(
        "hermes-agent-v0.7",
        "Hermes Agent",
        connections=[
            "闭环学习回路 → 曦和执行→记录→（断裂）→再执行",
            "技能自优化 → 酶阈值应从硬编码变为自适应",
        ],
        gaps=[
            "酶催化阈值目前在config.yml硬编码，应随使用频次自调",
            "模型提供商抽象层缺失，当前绑定Ollama",
        ],
    )
    print(f"已记录 {len(results)} 条精读反哺洞察")
    print(json.dumps([r["content"][:40] for r in results], indent=2, ensure_ascii=False))
