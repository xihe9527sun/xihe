#!/usr/bin/env python3
"""
曦和四原则酶约束 · Four Principles Enzyme Filter v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
将"去粗取精、去伪存真、由此及彼、由表及里"四个原则
编码为E1~E4酶的过滤条件，每次催化时自动执行。

设计:
  E1 (去粗取精) → 信息增益过滤：这条信息增加了多少赫布权重？
  E2 (去伪存真) → 一致性校验：这条信息与现有知识冲突吗？
  E3 (由此及彼) → 连接性检查：这条信息连接了几个现有节点？
  E4 (由表及里) → 架构层映射：这条信息对应哪个架构层？

集成方式:
  被 cascade_engine.py 的 E1~E4 酶执行时调用
  每个原则返回 (pass: bool, score: float, reason: str)

位置: F:/SmartLegend/Xihe/bridge/four_principles_enzyme.py
"""

import json, math
from pathlib import Path

XIHE_ROOT = Path("F:/SmartLegend/Xihe")
CORTEX_DIR = XIHE_ROOT / "cortex"

# ── E1: 去粗取精：信息增益过滤 ──
def principle_refine(data: dict) -> tuple:
    """
    评估一条信息是否"精"——即它带来了多少新认知。
    
    指标:
      - 新节点率: 是否引入了超图中不存在的新概念
      - 赫布增益: 连接了现有超图中的多少条路径
      - 信息密度: 长度vs信息量比值
    """
    score = 5.0  # 默认中等
    
    # 新概念检测
    new_concepts = data.get("new_concepts", [])
    if len(new_concepts) >= 3:
        score += 2.0
    elif len(new_concepts) >= 1:
        score += 1.0
    
    # 连接性
    connections = data.get("connections", [])
    if len(connections) >= 5:
        score += 2.0
    elif len(connections) >= 2:
        score += 1.0
    
    # 信息冗余额外扣分
    content_length = len(data.get("content", "") or "")
    if content_length > 5000 and len(connections) < 3:
        score -= 2.0
    
    return score >= 5.0, min(score, 10.0), f"E1:增益={score:.1f}"

# ── E2: 去伪存真：一致性校验 ──
def principle_verify(data: dict) -> tuple:
    """
    检查信息是否与现有知识一致。
    
    指标:
      - 矛盾检测: 是否与已入库宝藏观点冲突
      - 来源可信度: 来源的历史准确率
      - 自洽性: 内部逻辑是否一致
    """
    score = 5.0
    
    conflicts = data.get("conflicts", [])
    if len(conflicts) > 3:
        score -= 3.0
    elif len(conflicts) > 0:
        score -= 1.0
    
    source_trust = data.get("source_trust", 0.5)
    score += (source_trust - 0.5) * 4
    
    return score >= 4.0, min(score, 10.0), f"E2:一致={score:.1f}"

# ── E3: 由此及彼：连接性检查 ──
def principle_connect(data: dict) -> tuple:
    """
    检查这条信息能连接到多少现有知识节点。
    
    指标:
      - 跨域连接数: 连接了多少个不同领域
      - 桥接价值: 是否连接了原本不连通的两个模块
      - 拓扑嵌入度: 在超图中的嵌入质量
    """
    score = 5.0
    
    domains = data.get("domains", [])
    if len(domains) >= 3:
        score += 3.0
    elif len(domains) >= 2:
        score += 1.5
    
    bridges = data.get("bridges", [])
    if len(bridges) >= 1:
        score += 2.0
    
    return score >= 5.0, min(score, 10.0), f"E3:连接={score:.1f}"

# ── E4: 由表及里：架构层映射 ──
def principle_depth(data: dict) -> tuple:
    """
    评估信息触及了哪个架构层。
    
    层级:
      L1-L2: 表层信息（事件/新闻）→ 低分
      L3-L4: 结构信息（模式/趋势）→ 中等
      L5-L7: 深层信息（原理/架构）→ 高分
    """
    score = 5.0
    
    layer = data.get("layer", "L1")
    layer_map = {"L1": 2, "L2": 3, "L3": 5, "L4": 6, "L5": 8, "L6": 9, "L7": 10}
    score = layer_map.get(layer, 5)
    
    has_mechanism = data.get("has_mechanism", False)
    if has_mechanism:
        score += 1.0
    
    return score >= 5.0, min(score, 10.0), f"E4:深度={score:.1f}({layer})"

# ── 综合过滤 ──
def four_principles_filter(data: dict) -> dict:
    """
    四原则综合过滤。返回四项评分及是否通过。
    供 treasure_intake.py 和 cascade_engine.py 调用。
    """
    results = {
        "refine": principle_refine(data),
        "verify": principle_verify(data),
        "connect": principle_connect(data),
        "depth": principle_depth(data),
    }
    passed = all(r[0] for r in results.values())
    avg_score = sum(r[1] for r in results.values()) / 4
    return {
        "passed": passed,
        "average_score": round(avg_score, 1),
        "details": {k: {"pass": v[0], "score": v[1], "reason": v[2]} for k, v in results.items()},
    }

if __name__ == "__main__":
    # 测试数据
    test_data = {
        "content": "一篇关于自愈AI架构的深度论文，提出了一种基于超图反射弧的免疫机制",
        "new_concepts": ["reflex_arc", "health_hyperedge", "auto_immune_protocol"],
        "connections": ["metabolic_router", "self_reflection", "enzyme_cascade"],
        "domains": ["ai_architecture", "self_healing", "cognitive_science"],
        "bridges": ["metabolic_router ↔ self_reflection"],
        "layer": "L5",
        "has_mechanism": True,
        "source_trust": 0.8,
        "conflicts": [],
    }
    result = four_principles_filter(test_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
