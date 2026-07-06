"""
metacognitive.py — 曦和元认知层
17架构第15号：Metacognitive 元认知

核心能力：
  1. 能力边界感知 — 知道自己能做什么、不能做什么
  2. 置信度评估 — 对给定任务给出信心分数
  3. 拒绝/升级决策 — 根据规则决定执行/拒绝/移交人类

使用方式：
  from metacognitive import judge
  result = judge("帮我写一个React组件")  # → {decision, confidence, action}
"""

import json, os, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

XIHE_ROOT = Path("F:/SmartLegend/Xihe")
CORTEX = XIHE_ROOT / "cortex"
BJT = timezone(timedelta(hours=8))

# ── 加载能力注册表 ──

def load_registry():
    p = CORTEX / "capability-registry.json"
    try:
        c = open(p, encoding='utf-8').read()
        if c and c[0] == '\ufeff':
            c = c[1:]
        return json.loads(c)
    except:
        return {"capabilities": [], "refusal_rules": []}

# ── 任务分类 ──

TASK_PATTERNS = {
    "code_gen": [r"写[一|个|段]", r"生成.*代码", r"实现.*功能", r"构建.*(应用|程序)", r"create.*(app|func)", r"write.*code", r"implement"],
    "code_review": [r"审查.*代码", r"review.*code", r"检查.*代码", r"analyse.*code"],
    "architecture_design": [r"设计.*架构", r"架构.*方案", r"系统.*设计", r"顶层.*设计", r"方案.*设计"],
    "writing": [r"写.*文章", r"写.*博客", r"write.*article", r"write.*post", r"写.*内容"],
    "deep_read": [r"精读", r"deep.*read", r"分析.*论文", r"analyze.*paper", r"读懂"],
    "financial_analysis": [r"选股", r"股票.*分析", r"投资", r"financial", r"finance", r"股市", r"行情"],
    "file_ops": [r"读.*文件", r"写.*文件", r"创建.*文件", r"删除.*文件", r"read.*file", r"write.*file"],
    "network_api": [r"调用.*API", r"访问.*网站", r"curl", r"fetch.*url", r"网络请求"],
    "data_analysis": [r"分析.*数据", r"数据.*统计", r"analyze.*data", r"统计", r"可视化"],
    "design": [r"设计.*页面", r"UI.*设计", r"好看.*一点", r"design.*ui", r"美化"],
    "system_admin": [r"安装.*软件", r"系统.*配置", r"注册表", r"环境变量", r"system.*admin"],
    "legal": [r"法律", r"合同.*审查", r"legal", r"合规", r"是否.*合法"],
    "medical": [r"医疗", r"症状", r"生病", r"吃药", r"诊断", r"medical", r"symptom"],
}

def classify_task(task):
    """识别任务属于哪个能力类别"""
    task_lower = task.lower()
    for cap_id, patterns in TASK_PATTERNS.items():
        for p in patterns:
            if re.search(p, task_lower):
                return cap_id
    return None

# ── 置信度评估 ──

def estimate_confidence(task, cap_id=None):
    """估算对给定任务的置信度"""
    if not cap_id:
        cap_id = classify_task(task)
    
    registry = load_registry()
    
    # 找到匹配的能力
    if cap_id:
        for cap in registry["capabilities"]:
            if cap["id"] == cap_id:
                base = cap["confidence"]
                break
        else:
            base = 0.4  # 未知能力类别的保守估计
    else:
        base = 0.5  # 未分类任务的保守估计
    
    # 任务复杂度扣减
    complexity_penalty = 0.0
    if len(task) > 200:
        complexity_penalty += 0.15
    if "但不" in task or "except" in task.lower():
        complexity_penalty += 0.10
    if "多步" in task or "multi" in task.lower() or "复杂" in task:
        complexity_penalty += 0.10
    
    # 外部模式扣减
    mode_path = CORTEX / "mode.json"
    if mode_path.exists():
        try:
            mode = json.loads(open(mode_path).read())
            if mode.get("mode") == "external":
                complexity_penalty += 0.15
        except:
            pass
    
    confidence = max(0.05, min(0.98, base - complexity_penalty))
    return round(confidence, 2), cap_id

# ── 拒绝决策 ──

def judge(task, mode=None):
    """
    元认知判断入口
    
    返回:
      decision: "execute" | "refuse" | "escalate"
      confidence: 0-1
      cap_name: 匹配的能力名称
      reason: 判断理由
      message: 向用户展示的消息
    """
    registry = load_registry()
    confidence, cap_id = estimate_confidence(task)
    
    # 匹配能力信息
    cap_name = "未分类任务"
    cap_level = "unknown"
    for cap in registry["capabilities"]:
        if cap["id"] == cap_id:
            cap_name = cap["name"]
            cap_level = cap["level"]
            break
    
    # 读取当前模式
    if mode is None:
        mode_path = CORTEX / "mode.json"
        if mode_path.exists():
            try:
                mode = json.loads(open(mode_path).read()).get("mode", "internal")
            except:
                mode = "internal"
        else:
            mode = "internal"
    
    # 检查拒绝规则
    trigger_checks = {
        "涉及系统安全修改": re.search(r"系统安全|注册表|system32|内核|驱动|权限提升", task, re.I),
        "涉及法律/医疗建议": re.search(r"法律|律师|起诉|医疗|诊断|治疗|处方|手术|身体不舒服|生病|吃药|症状", task, re.I),
        "需要物理操作": re.search(r"打印|重启.*电脑|按下|插拔|连接.*硬件", task, re.I),
    }
    
    for trigger, matched in trigger_checks.items():
        if matched:
            for rule in registry["refusal_rules"]:
                if rule["trigger"] == trigger:
                    return {
                        "decision": "refuse",
                        "confidence": confidence,
                        "cap_id": cap_id,
                        "cap_name": cap_name,
                        "cap_level": cap_level,
                        "reason": f"触犯拒绝规则: {trigger}",
                        "message": rule["message"],
                    }
    
    # 置信度决策
    if confidence < 0.3:
        return {
            "decision": "refuse",
            "confidence": confidence,
            "cap_id": cap_id,
            "cap_name": cap_name,
            "cap_level": cap_level,
            "reason": f"置信度过低({confidence})",
            "message": "这个任务超出了我的能力范围，建议由盘古直接处理。",
        }
    
    if mode == "external" and confidence < 0.7:
        return {
            "decision": "escalate",
            "confidence": confidence,
            "cap_id": cap_id,
            "cap_name": cap_name,
            "cap_level": cap_level,
            "reason": f"对外模式+置信度不足({confidence}<0.7)",
            "message": f"在对外模式下，我对这个任务({cap_name})信心不足({confidence:.0%})，请确认是否继续。",
        }
    
    if confidence < 0.6:
        return {
            "decision": "escalate",
            "confidence": confidence,
            "cap_id": cap_id,
            "cap_name": cap_name,
            "cap_level": cap_level,
            "reason": f"置信度中等({confidence})",
            "message": f"这个任务({cap_name})我有{confidence:.0%}的把握，建议盘古复核一下再执行。",
        }
    
    return {
        "decision": "execute",
        "confidence": confidence,
        "cap_id": cap_id,
        "cap_name": cap_name,
        "cap_level": cap_level,
        "reason": f"置信度充足({confidence})",
        "message": None,
    }

# ── 自检报告 ──

def self_report():
    """生成元认知自检报告"""
    registry = load_registry()
    caps = registry["capabilities"]
    
    high = sum(1 for c in caps if c["level"] == "high")
    mid = sum(1 for c in caps if c["level"] == "medium")
    low = sum(1 for c in caps if c["level"] == "low")
    
    return {
        "report_at": datetime.now(BJT).isoformat(),
        "total_capabilities": len(caps),
        "high_confidence": high,
        "medium_confidence": mid,
        "low_confidence": low,
        "refusal_rules": len(registry["refusal_rules"]),
        "avg_confidence": round(sum(c["confidence"] for c in caps) / len(caps), 2) if caps else 0,
    }

if __name__ == "__main__":
    import sys
    tests = [
        "写一个React状态管理库",
        "帮我分析一下A股行情",
        "帮我设计曦和的下一代架构",
        "修改系统注册表优化性能",
        "我身体不舒服，帮我看看是什么病",
        "帮我审查一下这份法律合同的条款",
    ]
    print("=== 曦和元认知测试 ===")
    print(f"能力总数: {len(load_registry()['capabilities'])} 类")
    print(f"拒绝规则: {len(load_registry()['refusal_rules'])} 条\n")
    for t in tests:
        r = judge(t)
        icon = {"execute": "✅", "refuse": "❌", "escalate": "⚠️"}[r["decision"]]
        print(f"{icon} [{r['decision']:8}] ({r['confidence']:.0%}) {r['cap_name']:10s} | {t[:30]}...")
    print(f"\n=== 元认知健康 ===")
    sr = self_report()
    print(f"高置信度: {sr['high_confidence']} | 中: {sr['medium_confidence']} | 低: {sr['low_confidence']}")
    print(f"平均置信度: {sr['avg_confidence']}")
