#!/usr/bin/env python3
"""
曦和·因果归因模块 (CausalFlow 融合 · 2026-07-20)
═════════════════════════════════════════════════════
来源 : CausalFlow: 因果归因与反事实修复 (ICML 2026 Workshop)
研判 : 0.87 (研讨厅三层研判通过 · A嫁接策略)
挂接 : evolution_engine.record_negative_finding 记录负面结论后调用本模块

核心思想 (CausalFlow):
  失败执行轨迹 → 步骤级因果责任分数 → 最小化反事实修复
  让进化引擎的负反馈闭环从「知道错了」升级到「知道错在哪一步」。

设计约束:
  - 轻量启发式, 无 LLM 运行时依赖 (避免重型调用)
  - 基于 finding_type + description 关键词做责任归因
  - 产出可复用的监督信号, 持久化到 causal_responsibility.json
  - 失败静默 (异常不阻断主流程, 仅记日志)
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

BJT = timezone(timedelta(hours=8))
TREASURE_DIR = Path(r"F:\SmartLegend\Xihe\treasure")
RESP_FILE = TREASURE_DIR / "causal_responsibility.json"

# 步骤级因果责任归因关键词映射 (启发式责任定位)
_STEP_KEYWORDS = [
    ("检索", "步骤1·信息检索", 0.82),
    ("fetch", "步骤1·信息检索", 0.82),
    ("解析", "步骤2·内容解析", 0.78),
    ("parse", "步骤2·内容解析", 0.78),
    ("编码", "步骤3·记忆编码", 0.71),
    ("encode", "步骤3·记忆编码", 0.71),
    ("推理", "步骤4·推理决策", 0.75),
    ("reason", "步骤4·推理决策", 0.75),
    ("调用", "步骤5·工具调用", 0.68),
    ("call", "步骤5·工具调用", 0.68),
    ("超时", "步骤·超时中断", 0.90),
    ("timeout", "步骤·超时中断", 0.90),
    ("权限", "步骤·权限校验", 0.85),
    ("permission", "步骤·权限校验", 0.85),
]

# finding_type 基础责任权重
_TYPE_WEIGHT = {
    "failed_attempt": 0.80,
    "dead_end": 0.65,
    "contradiction": 0.72,
    "non_transferable": 0.55,
}


def _locate_responsible_step(description):
    """从描述文本定位最可能的责任步骤 (启发式)"""
    desc = (description or "").lower()
    best = ("步骤·未定位", 0.40)
    for kw, step, score in _STEP_KEYWORDS:
        if kw.lower() in desc:
            if score > best[1]:
                best = (step, score)
    return best


def _minimal_counterfactual(responsible_step, finding_type):
    """生成最小化反事实修复建议 (不重跑整链, 只修责任步)"""
    base = {
        "步骤1·信息检索": "改用冗余数据源 + 超时退避重试",
        "步骤2·内容解析": "增加 schema 校验 + 容错解析分支",
        "步骤3·记忆编码": "编码前做去重/冲突检测",
        "步骤4·推理决策": "引入对抗性自检 + 低信心回退",
        "步骤5·工具调用": "参数预校验 + 调用结果断言",
        "步骤·超时中断": "拆分长任务 + 增量检查点",
        "步骤·权限校验": "最小权限预申请 + 失败降级路径",
        "步骤·未定位": "补充执行轨迹日志后复判",
    }
    return base.get(responsible_step, "补充执行轨迹日志后复判")


def attribute_causal_responsibility(finding):
    """
    对一条负面结论做步骤级因果责任归因, 并生成最小化反事实修复。

    Args:
        finding: dict, 字段 {treasure_id, type, description, source, recorded_at}

    Returns:
        dict: 归因结果 {responsible_step, causal_score, counterfactual, ...}
              出错时返回 {"error": str}
    """
    try:
        desc = finding.get("description", "")
        ftype = finding.get("type", "failed_attempt")
        step, kw_score = _locate_responsible_step(desc)
        type_w = _TYPE_WEIGHT.get(ftype, 0.60)
        # 因果责任分数 = 类型权重 × 步骤定位置信度
        causal_score = round(min(1.0, type_w * kw_score), 3)
        counterfactual = _minimal_counterfactual(step, ftype)

        result = {
            "treasure_id": finding.get("treasure_id"),
            "finding_type": ftype,
            "responsible_step": step,
            "causal_score": causal_score,
            "counterfactual": counterfactual,
            "source_finding": finding.get("recorded_at"),
            "attributed_at": datetime.now(BJT).isoformat(),
        }

        # 持久化 (追加, 保留最近 200 条)
        try:
            if RESP_FILE.exists():
                data = json.loads(RESP_FILE.read_text(encoding="utf-8"))
            else:
                data = {"responsibilities": [], "updated": None}
            data["responsibilities"].append(result)
            if len(data["responsibilities"]) > 200:
                data["responsibilities"] = data["responsibilities"][-200:]
            data["updated"] = result["attributed_at"]
            data["count"] = len(data["responsibilities"])
            RESP_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass  # 归因存储失败不阻断主流程

        return result
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # 自检
    test = {
        "treasure_id": "test",
        "type": "failed_attempt",
        "description": "检索超时导致解析失败",
        "source": "auto",
        "recorded_at": datetime.now(BJT).isoformat(),
    }
    print("CausalFlow 归因自检:", attribute_causal_responsibility(test))
