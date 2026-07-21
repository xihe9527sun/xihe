#!/usr/bin/env python3
"""
rrif_gate_modulator.py — RRIF 门控调制器 v2
CATS Net CA 模块启发的注意力门控系统

9维关系注意力向量 + D10 可信度门控（OWASP ASI06/09 合规）

D1 = 关联度    — 当前上下文与皮层节点的匹配程度
D2 = 兴趣匹配  — 盘古的兴趣倾向匹配
D3 = 中文亲近  — 中文原生计划权重
D4 = 物距      — 话题与当前任务的物理/逻辑距离
D5 = 跨界度    — 跨域连接的需求强度
D6 = 新颖度    — 信息的陌生程度
D7 = 张力      — 认知冲突/矛盾强度
D8 = 紧迫度    — 时间敏感度/优先级
D9 = 边界渗透度 — 信息跨越认知边界的意愿（实验 · w=0.15）
D10= 可信度门控 — 信息来源/Connector 的信任评分（OWASP · w=0.20）
"""
import json
from pathlib import Path

XIHE_HOME = Path(__file__).parent.parent
TRUST_REGISTRY = XIHE_HOME / "bridge" / "trust-registry.json"

# 默认权重（可被配置覆盖）
DEFAULT_WEIGHTS = {
    "D1": 1.0,   # 关联度
    "D2": 0.8,   # 兴趣匹配
    "D3": 1.5,   # 中文亲近（中文原生计划期间 x1.5）
    "D4": 0.6,   # 物距
    "D5": 0.7,   # 跨界度
    "D6": 0.5,   # 新颖度
    "D7": 0.4,   # 张力
    "D8": 0.3,   # 紧迫度
    "D9": 0.15,  # 边界渗透度（实验）
    "D10": 0.20, # 可信度门控（NEW · OWASP）
}

# Connector 信任等级到 D10 评分的映射
TRUST_TO_SCORE = {
    "trusted":    1.0,   # 完全可信 → 不降权
    "vetted":     0.8,   # 已验证 → 轻度降权
    "community":  0.5,   # 社区 → 中度降权
    "untrusted":  0.2,   # 不可信 → 重度降权
    "unknown":    0.1,   # 未知 → 几乎阻断
}


def load_trust_registry() -> dict:
    """加载信任注册表"""
    if TRUST_REGISTRY.exists():
        try:
            return json.loads(TRUST_REGISTRY.read_text(encoding="utf-8"))
        except:
            pass
    return {"connectors": []}


def get_trust_score(source_id: str, trust_registry: dict = None) -> float:
    """查询指定来源的 D10 可信度评分"""
    if trust_registry is None:
        trust_registry = load_trust_registry()

    connectors = trust_registry.get("connectors", [])
    for c in connectors:
        if c.get("id") == source_id:
            level = c.get("trust_level", "unknown")
            return TRUST_TO_SCORE.get(level, 0.1)

    # 未注册来源 → 最低信任
    return TRUST_TO_SCORE["unknown"]


class GateModulator:
    """RRIF 门控调制器 — 10维注意力向量"""

    def __init__(self, weights: dict = None):
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.trust_registry = load_trust_registry()

    def compute_vector(self, context: dict) -> dict:
        """计算 10 维注意力向量
        
        参数:
          context: {
            "relevance": float,      # D1 关联度 0-1
            "interest": float,       # D2 兴趣匹配 0-1
            "chinese_affinity": float, # D3 中文亲近 0-1
            "distance": float,       # D4 物距 0-1
            "cross_domain": float,   # D5 跨界度 0-1
            "novelty": float,        # D6 新颖度 0-1
            "tension": float,        # D7 张力 0-1
            "urgency": float,        # D8 紧迫度 0-1
            "boundary_penetration": float, # D9 边界渗透度 0-1
            "source_id": str,        # D10 信息来源ID
            "source_trust": float,   # D10 可选：直接指定信任分
          }
        """
        vector = {}

        # D1-D9: 基础注意力维度
        vector["D1"] = context.get("relevance", 0.5) * self.weights["D1"]
        vector["D2"] = context.get("interest", 0.5) * self.weights["D2"]
        vector["D3"] = context.get("chinese_affinity", 0.5) * self.weights["D3"]
        vector["D4"] = context.get("distance", 0.5) * self.weights["D4"]
        vector["D5"] = context.get("cross_domain", 0.5) * self.weights["D5"]
        vector["D6"] = context.get("novelty", 0.5) * self.weights["D6"]
        vector["D7"] = context.get("tension", 0.5) * self.weights["D7"]
        vector["D8"] = context.get("urgency", 0.5) * self.weights["D8"]
        vector["D9"] = context.get("boundary_penetration", 0.5) * self.weights["D9"]

        # D10: 可信度门控 — 从 source_id 查表或直接使用 source_trust
        if "source_trust" in context:
            raw_trust = context["source_trust"]
        elif "source_id" in context:
            raw_trust = get_trust_score(context["source_id"], self.trust_registry)
        else:
            raw_trust = 0.5  # 无来源信息 → 中等信任

        vector["D10"] = raw_trust * self.weights["D10"]

        # 总分：加权注意力总和
        vector["total"] = sum(vector.values())
        vector["trust_gate_raw"] = raw_trust
        vector["trust_gate_active"] = raw_trust < 0.6

        return vector

    def should_block(self, vector: dict, threshold: float = 0.3) -> bool:
        """D10 可信度门控阻断判断"""
        if not vector.get("trust_gate_active", False):
            return False  # 信任足够，不阻断
        # D10 加权后的值低于阈值 → 阻断
        return vector.get("D10", 1.0) < threshold * self.weights["D10"]

    def score_connector(self, source_id: str) -> dict:
        """对指定 Connector 输出 D10 评分报告"""
        score = get_trust_score(source_id, self.trust_registry)
        level = "unknown"
        for c in self.trust_registry.get("connectors", []):
            if c.get("id") == source_id:
                level = c.get("trust_level", "unknown")
                break
        return {
            "source_id": source_id,
            "trust_level": level,
            "d10_score": round(score, 2),
            "d10_weighted": round(score * self.weights["D10"], 3),
            "blocked": score < 0.3,
        }




    def plan_time_reflection(self, plan_draft, historical_errors=None):
        """
        [PreFlect 融合 · 研讨厅研判 0.85 · C.补充 · 2026-07-21]
        PreFlect (arXiv:2602.07187) 事前反思(plan-phase reflection)。
        把自反层从『act→fail→reflect→recover』前移到『plan→critique→revise→execute』，
        对 D2 兴趣匹配维度做 plan-time 增强——与既有 compute_vector 门控正交不撞车。

        机制: 从历史 agent 轨迹蒸馏 recurring success/failure patterns,
        对 plan_draft 做 plan-phase critique(在不可逆执行前拦截潜在错误)。

        参数:
            plan_draft: dict 待执行计划 {steps: [...], goal: str}
            historical_errors: list[str] 历史失败模式(可选, 缺省用内置常见模式)
        返回: {"critiques": list[str], "risk_score": float}
        """
        DEFAULT_ERR = [
            "检索超时导致后续解析失败",
            "权限不足时未预申请最小权限",
            "长任务未拆分检查点",
            "跨 agent 上下文未传递致重复劳动",
            "低信心决策未触发回退",
        ]
        errs = historical_errors or DEFAULT_ERR
        critiques = []
        steps = plan_draft.get("steps", []) if isinstance(plan_draft, dict) else []
        goal = plan_draft.get("goal", "") if isinstance(plan_draft, dict) else str(plan_draft)
        for e in errs:
            kw = e.split()[0] if ' ' in e else e[:4]  # 中文无空格, 取前4字作匹配模式
            if any(kw in str(s) for s in steps):
                critiques.append("潜在风险(事前): " + e)
        if not steps:
            critiques.append("计划未拆解为步骤, 执行前建议先分解(避免不可逆试错成本)")
        risk_score = round(min(1.0, len(critiques) / max(1, len(errs))), 3)
        return {"critiques": critiques, "risk_score": risk_score, "goal": goal}

    def cost_ladder(self, context: dict) -> dict:
        """
        [腾讯五步定位法融合 · 研讨厅研判 0.84(不整套吸收)→轻量补丁 · 2026-07-21]
        分步消耗检索: 根据上下文决定检索深度(1-5级), 每级对应不同 token 消耗。
        对应腾讯『五步定位法』的 300 倍 token 压缩思想——先廉价广撒网, 失败再加深,
        绝不一开始就全量读源码。增强 D4 物距 / D6 新颖度 维度的检索经济性。

        级别定义(估算 token 消耗, 仅供调度参考):
          L1 = 仅看目录名/模块名           ~50
          L2 = 看模块描述/README 首段       ~300
          L3 = 脚本级 grep 关键词           ~800
          L4 = 读源码关键函数               ~2500
          L5 = 增量验证(实际运行自测)        ~6000

        决策逻辑:
          近(物距小) + 已知(新颖度低) + 不急 → 浅(L1-L2)
          远(物距大) + 新颖(新颖度高) + 急   → 深(L4-L5)
        返回: {"level": int, "est_cost_tokens": int, "rationale": str}
        """
        distance = context.get("distance", 0.5)      # D4 物距 0-1 (大=远)
        novelty = context.get("novelty", 0.5)        # D6 新颖度 0-1
        urgency = context.get("urgency", 0.3)        # D8 紧迫度 0-1

        # 深度评分: 远+新颖推深, 急迫也推深
        depth_score = (distance * 0.45 + novelty * 0.40 + urgency * 0.15)
        if depth_score < 0.30:
            level = 1
        elif depth_score < 0.45:
            level = 2
        elif depth_score < 0.60:
            level = 3
        elif depth_score < 0.78:
            level = 4
        else:
            level = 5

        cost_table = {1: 50, 2: 300, 3: 800, 4: 2500, 5: 6000}
        rationale = (
            f"物距={distance:.2f} 新颖={novelty:.2f} 紧迫={urgency:.2f} "
            f"→ 深度分={depth_score:.2f} → 取 L{level}"
        )
        return {
            "level": level,
            "est_cost_tokens": cost_table[level],
            "rationale": rationale,
        }
# ── 边界测试 ──

def run_boundary_test():
    """测试 D10 在不同信任等级下的行为"""
    print("=" * 60)
    print("  D10 可信度门控 · 边界测试")
    print("=" * 60)

    modulator = GateModulator()

    test_cases = [
        # (source_id, label, expected_trust)
        ("github",        "GitHub (trusted)",     1.0),
        ("tencent-docs",  "腾讯文档 (trusted)",    1.0),
        ("netease-mail",  "网易邮箱 (vetted)",     0.8),
        ("tyc-mcp",       "天眼查 (vetted)",       0.8),
        ("weisheng-scrm", "微盛SCRM (community)",  0.5),
        ("unknown-mcp",   "未注册来源",             0.1),
    ]

    print(f"\n{'来源':<25} {'等级':<12} {'D10原始':<8} {'加权':<8} {'阻断':<6}")
    print("-" * 60)
    for sid, label, expected in test_cases:
        vec = modulator.compute_vector({"source_id": sid})
        blocked = modulator.should_block(vec)
        print(f"{label:<25} {vec['trust_gate_raw']:<12.2f} "
              f"{vec['D10']:<8.3f} {vec['trust_gate_raw'] * modulator.weights['D10']:<8.3f} "
              f"{'⛔' if blocked else '✅':<6}")

    # 测试模拟不可信工具的阻断场景
    print(f"\n=== 场景测试：不可信 Connector 返回结果 ===")
    untrusted_vec = modulator.compute_vector({
        "source_id": "unknown-mcp",
        "relevance": 0.9,    # 内容很相关
        "interest": 0.8,     # 盘古感兴趣
        "novelty": 0.9,      # 很新颖
    })
    print(f"场景：内容高度相关(0.9)但来源不可信(0.1)")
    print(f"  D1-D9 总分: {sum(v for k,v in untrusted_vec.items() if k.startswith('D') and k != 'D10'):.3f}")
    print(f"  D10 加权值: {untrusted_vec['D10']:.3f}")
    print(f"  总分: {untrusted_vec['total']:.3f}")
    print(f"  阻断: {'⛔ 不会进入上下文' if modulator.should_block(untrusted_vec) else '✅ 允许'}")

    # 测试社区 Connector 的中等信任场景
    comm_vec = modulator.compute_vector({
        "source_id": "weisheng-scrm",
        "relevance": 0.6,
    })
    print(f"\n场景：社区Connector(信任0.5) + 中等相关(0.6)")
    print(f"  D10 加权值: {comm_vec['D10']:.3f}")
    print(f"  D10原始: {comm_vec['trust_gate_raw']:.2f}")
    print(f"  阻断: {'⛔' if modulator.should_block(comm_vec) else '✅ 允许但降权'}")

    return modulator


if __name__ == "__main__":
    run_boundary_test()
