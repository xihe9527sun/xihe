#!/usr/bin/env python3
"""
曦和每日生长计划 · Daily Plan v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
每天自动生成生长计划，作为超图节点写入。
代谢路由会遍历计划节点，引导当天的注意力分配。

执行时机:
  - 每天早上8:00（由daily_health.py顺带触发）
  - 每次session启动时（由session-start协议触发）

输出:
  - cortex/daily-plan.json: 今天的计划结构
  - 此文件可由 bridge-daemon 读入，注入 session context

计划结构:
  - 今天要长的能力（基于昨天的薄弱点）
  - 觅食方向（基于知识图谱的稀疏区域）
  - 自检指标（今天结束时该达到的状态）

位置: F:/SmartLegend/Xihe/bridge/daily_plan.py
"""

import json, time, os
from pathlib import Path
from datetime import datetime, timezone, timedelta

XIHE_ROOT = Path("F:/SmartLegend/Xihe")
CORTEX_DIR = XIHE_ROOT / "cortex"
BRIDGE_DIR = XIHE_ROOT / "bridge"
LOG_DIR = XIHE_ROOT / "logs"
BJT = timezone(timedelta(hours=8))

PLAN_PATH = CORTEX_DIR / "daily-plan.json"
HISTORY_PATH = LOG_DIR / "daily-plans.jsonl"

def analyze_weakness():
    """分析薄弱区域（基于昨天的自反层数据）"""
    weakness = []
    # 1. 检查互信息时滞
    try:
        health = json.loads(open(CORTEX_DIR / "health-status.json", "r", encoding="utf-8").read())
        if health.get("lag_seconds", 0) > 300:
            weakness.append("health_monitoring")
    except: 
        weakness.append("health_reflex_not_ready")
    
    # 2. 检查宝藏消化率
    try:
        ti = json.loads(open(XIHE_ROOT / "treasure" / "index.json", "r", encoding="utf-8-sig").read())
        total = len(ti.get("treasures", []))
        digested = sum(1 for t in ti.get("treasures", []) if t.get("status") == "digested")
        if total > 0 and digested / total < 0.5:
            weakness.append("treasure_digestion")
    except:
        weakness.append("treasure_index_unreadable")
    
    return weakness

def analyze_forage_directions():
    """推荐觅食方向（基于知识图谱薄弱域）"""
    # 默认方向
    directions = [
        {"area": "agent_architecture", "reason": "架构升级后需要外部验证", "urgency": 8},
        {"area": "self_healing_systems", "reason": "自愈体系刚启动，需更多参考", "urgency": 9},
        {"area": "cognitive_architecture", "reason": "长期关注领域", "urgency": 6},
    ]
    return directions

def generate_plan():
    """生成今天的生长计划"""
    today = datetime.now(BJT).strftime("%Y-%m-%d")
    
    # 加载昨天的计划（如果有）
    yesterday_plan = None
    try:
        yesterday_plan = json.loads(open(PLAN_PATH, "r", encoding="utf-8").read())
    except:
        pass
    
    weakness = analyze_weakness()
    directions = analyze_forage_directions()
    
    plan = {
        "date": today,
        "generated_at": datetime.now(BJT).isoformat(),
        "version": 2,
        "status": "active",
        "weakness_areas": weakness,
        "focus": {
            "primary": directions[0]["area"] if directions else "general",
            "secondary": [d["area"] for d in directions[1:3]],
        },
        "forage_directions": directions,
        "health_targets": {
            "max_lag_seconds": 60,        # 目标：心跳时滞不超过60s
            "min_port_alive": 5,           # 目标：5端口全通
            "min_digestion_rate": 0.5,     # 目标：50%以上宝藏已消化
        },
        "self_check": {
            "morning": ["ports_all_alive", "lag_under_60s", "yesterday_plan_reviewed"],
            "evening": ["articles_written_today", "forage_completed", "lag_review"],
        },
        # 昨天复盘
        "yesterday_review": None,
        "continuity": {
            "previous_plan": yesterday_plan.get("date") if yesterday_plan else None,
            "carry_over": yesterday_plan.get("focus") if yesterday_plan else None,
        }
    }
    
    # 写计划
    CORTEX_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(PLAN_PATH, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    
    # 追加历史
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"date": today, "plan": plan}, ensure_ascii=False) + "\n")
    
    return plan

if __name__ == "__main__":
    plan = generate_plan()
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    print(f"\n✅ 今日计划已生成: {plan['date']}")
    print(f"  薄弱区域: {', '.join(plan['weakness_areas']) if plan['weakness_areas'] else '暂无'}")
    print(f"  主要方向: {plan['focus']['primary']}")
