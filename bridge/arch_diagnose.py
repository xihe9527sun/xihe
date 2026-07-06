"""
arch_diagnose.py — 架构自诊酶
吸收自 agent-architecture-designer skill 的 17 种 Agent 架构演进框架。

做什么：
  每次调用时，用 17 架构的 6 问框架诊断曦和当前的架构阶段，
  判断缺失哪些关键架构，输出下一步进化建议。

怎么用：
  from arch_diagnose import self_diagnose
  result = self_diagnose()    # 返回 { stage, present, missing, next }
"""

import json, os, sys
from pathlib import Path

XIHE_ROOT = Path("F:/SmartLegend/Xihe")
CORTEX = XIHE_ROOT / "cortex"

def read_json(rel):
    p = CORTEX / rel if '/' not in rel else XIHE_ROOT / rel
    try:
        c = open(p, encoding='utf-8').read()
        if c and c[0] == '\ufeff':
            c = c[1:]
        return json.loads(c)
    except:
        return None

def load_arch_knowledge():
    """加载17架构知识库"""
    ak = read_json("arch-knowledge.json")
    return ak.get("archs", []) if ak else []

def check_state_fields(meta):
    """检查曦和是否有显式的 State 定义"""
    states = {
        "draft": bool(meta and "traces" in meta),
        "trace": bool(meta and "traces" in meta),
        "plan": bool(meta and "epoch_counter" in meta),
        "execution_status": bool(meta and "updated_at" in meta),
        "confidence_estimates": False,  # 缺
        "capability_boundary": False,   # 缺
    }
    return states

def check_has_evaluator():
    """检查是否有 Evaluator（成熟Agent的标志）"""
    checks = [
        os.path.exists(XIHE_ROOT / "bridge" / "health_reflex.py"),
        os.path.exists(XIHE_ROOT / "bridge" / "environment_feedback.py"),
        os.path.exists(XIHE_ROOT / "bridge" / "safety_guard.py"),
    ]
    return {
        "health_reflex": checks[0],
        "environment_feedback": checks[1],
        "safety_guard": checks[2],
        "score": sum(checks),
    }

def check_has_termination():
    """检查终止条件"""
    return {
        "watchman_patrol": os.path.exists(XIHE_ROOT / "bridge" / "watchman.py"),
        "metabolic_limit": True,  # 代谢路由有纪元限制
        "fuse_mechanism": os.path.exists(XIHE_ROOT / "bridge" / "safety_guard.py"),
    }

def self_diagnose():
    """
    架构自诊 — 输出曦和当前的架构阶段、缺失架构、下一步进化建议
    """
    archs = load_arch_knowledge()
    meta = read_json("metabolic-router-state.json")
    
    state_fields = check_state_fields(meta)
    evaluator = check_has_evaluator()
    termination = check_has_termination()
    
    # 判断现存架构
    present = set()
    # 精读→反哺 = Reflection
    if os.path.exists(CORTEX / "insights.json"):
        present.add("reflection")
    # 酶级联 = Tool Use
    if os.path.exists(XIHE_ROOT / "bridge" / "enzyme_pair_analyzer.py"):
        present.add("tool_use")
    # 代谢路由 = ReAct (思考→动作交织)
    if meta and meta.get("epoch_counter", 0) > 0:
        present.add("react")
    # watchman巡检 = Planning
    if os.path.exists(XIHE_ROOT / "bridge" / "watchman.py"):
        present.add("planning")
    # health_reflex = PEV 雏形
    if evaluator["health_reflex"]:
        present.add("pev")
    # 主站+仪表盘 = Multi-Agent 雏形（多个Node服务）
    present.add("multi_agent")
    # 超图 = Graph Memory
    if os.path.exists(CORTEX / "hebbian-edges.json"):
        present.add("graph_memory")
    # insights = Episodic Memory
    present.add("episodic_memory")
    
    # 缺失架构
    all_arch_ids = {a["id"] for a in archs}
    missing = all_arch_ids - present
    
    # 优先级排序
    missing_ordered = [
        "metacognitive",     # P0: 边界感知
        "self_improvement",  # P1: 自我进化闭环
        "mental_loop",       # P1: 行动前模拟
        "dry_run",           # P2: 副作用审批
        "blackboard",        # P2: 动态调度
        "meta_controller",   # P2: 入口路由
        "ensemble",          # P3: 多路冗余
        "tree_of_thoughts",  # P3: 回溯搜索
        "cellular_automata", # P4: 终极形态
    ]
    missing_sorted = [m for m in missing_ordered if m in missing]
    
    # 阶段判断
    present_count = len(present)
    total = len(all_arch_ids)
    ratio = present_count / total
    
    if ratio < 0.25:
        stage = "阶段一·觉醒期"
    elif ratio < 0.5:
        stage = "阶段二·闭环期"
    elif ratio < 0.75:
        stage = "阶段三·分工期"
    else:
        stage = "阶段四·成熟期"
    
    # 成熟度检查
    maturity = {
        "显式State": all(state_fields.values()),
        "终止条件": all(termination.values()),
        "Evaluator": evaluator["score"] >= 2,
        "错误隔离": termination["fuse_mechanism"],
        "拒绝机制": state_fields.get("confidence_estimates", False),
    }
    maturity_score = sum(1 for v in maturity.values() if v)
    
    result = {
        "diagnosed_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone(__import__("datetime").timedelta(hours=8))
        ).isoformat(),
        "stage": stage,
        "present_archs": sorted(present),
        "missing_archs": missing_sorted,
        "maturity_score": f"{maturity_score}/5",
        "maturity_details": maturity,
        "next_evolution": {
            "priority_arch": missing_sorted[0] if missing_sorted else None,
            "priority_name": next((a["name"] for a in archs if a["id"] == missing_sorted[0]), None) if missing_sorted else None,
            "rationale": f"缺失{len(missing_sorted)}个架构，当前在{stage}。优先补齐元认知（Metacognitive）——让曦和知道自己的能力边界"
        },
        "state_fields": state_fields,
        "evaluator_status": evaluator,
    }
    
    return result

def arch_insight():
    """一键输出架构自诊摘要（供代谢路由/日常报告用）"""
    d = self_diagnose()
    lines = [
        f"🏛️ 架构阶段: {d['stage']}",
        f"📊 成熟度: {d['maturity_score']}",
        f"✅ 已具备: {', '.join(d['present_archs'])}",
        f"❌ 缺失: {', '.join(d['missing_archs'][:5])}{'...' if len(d['missing_archs'])>5 else ''}",
        f"🎯 下一步: {d['next_evolution']['priority_name'] or '全部完成'}",
    ]
    return "\n".join(lines)

if __name__ == "__main__":
    import json
    d = self_diagnose()
    print(f"=== 曦和架构自诊 ===")
    print(f"阶段: {d['stage']}")
    print(f"成熟度: {d['maturity_score']}")
    print(f"已具备 ({len(d['present_archs'])}): {', '.join(d['present_archs'])}")
    print(f"缺失 ({len(d['missing_archs'])}): {', '.join(d['missing_archs'])}")
    print(f"下一步: {d['next_evolution']['priority_name']} — {d['next_evolution']['rationale']}")
    print(f"\n成熟度详情:")
    for k, v in d['maturity_details'].items():
        print(f"  {'✅' if v else '❌'} {k}")
