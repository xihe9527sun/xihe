#!/usr/bin/env python3
"""
pre_merge_checklist.py — 融合前红线预检 (腾讯红线机制融合 · 轻量补丁 · 2026-07-21)
[研讨厅研判 0.84(不整套吸收) → 工程补丁]

任何『新增/修改/升格/融合/吸收』系统组件的操作, 落盘前必须先过本预检。
把曦和顶层铁律前置为可执行校验, 而非事后审查——对应腾讯 Skill 系统的『红线机制』。

红线清单(任一条命中即拒绝落盘):
  R1  研讨厅研判分 ≥ 0.85 (外部吸收必须; 盘古显式敕令豁免)
  R2  非破坏性: 禁止删系统核心文件 / 硬编码 session id / 无差别 taskkill
  R3  有落点调研: 已知目标模块, 非盲目新建
  R4  不重复造轮子: 不与现有构件功能重叠
  R5  最小侵入: 改动幅度受控, 非整文件重写

用法:
  from pre_merge_checklist import pre_merge_checklist
  res = pre_merge_checklist(change)
  if not res["passed"]:
      raise RuntimeError("红线拦截: " + "; ".join(res["violations"]))
"""
import re

# 红线定义: (id, 描述, 检查函数)
# 检查函数接收 change dict, 返回 (passed: bool, detail: str)
RED_LINES = [
    ("R1", "研讨厅研判分 ≥ 0.85（外部吸收）"),
    ("R2", "非破坏性：不删核心文件/不硬编码session/无差别taskkill"),
    ("R3", "有落点调研：已知目标模块"),
    ("R4", "不重复造轮子：不与现有构件重叠"),
    ("R5", "最小侵入：改动幅度受控"),
]

# 破坏性特征正则（命中即视为高危）
_DESTRUCTIVE_PATTERNS = [
    (r"session", "硬编码 session id 判定当前会话"),
    (r"taskkill", "无差别 taskkill（按进程名/非白名单批量杀）"),
    (r"rm\s+-rf|del\s+/S|rmtree|shutil\.rmtree", "递归删除系统目录"),
    (r"__pycache__", "清理 __pycache__ 以外的系统文件"),
]


def _check_r1(change: dict) -> tuple:
    """研讨厅分门槛"""
    if change.get("pangu_exempt"):
        return True, "盘古显式敕令豁免"
    score = change.get("seminar_score")
    if score is None:
        return False, "未提供研讨厅研判分（外部吸收必须走研判）"
    if score < 0.85:
        return False, f"研判分 {score} < 0.85 门槛"
    return True, f"研判分 {score} ≥ 0.85"


def _check_r2(change: dict) -> tuple:
    """非破坏性"""
    diff = change.get("diff_text", "") or change.get("code", "")
    for pat, desc in _DESTRUCTIVE_PATTERNS:
        if re.search(pat, diff, re.IGNORECASE):
            return False, f"检测到破坏性特征: {desc}"
    # 显式声明 is_destructive 时阻断
    if change.get("is_destructive"):
        return False, "变更自报 is_destructive=True"
    return True, "无可疑破坏性特征"


def _check_r3(change: dict) -> tuple:
    """落点调研"""
    target = change.get("target")
    if not target:
        return False, "未指定目标模块（落点调研缺失）"
    return True, f"目标模块: {target}"


def _check_r4(change: dict) -> tuple:
    """不重复造轮子"""
    if change.get("duplicates_existing"):
        return False, f"与现有构件重叠: {change.get('duplicates_existing')}"
    return True, "未检测到功能重叠"


def _check_r5(change: dict) -> tuple:
    """最小侵入"""
    diff_size = change.get("diff_size", 0)
    cap = change.get("diff_cap", 400)  # 默认单变更 ≤400 行视为受控
    if isinstance(diff_size, int) and diff_size > cap:
        return False, f"改动 {diff_size} 行 > 阈值 {cap}（疑似整文件重写）"
    return True, f"改动幅度受控({diff_size} 行)"


_CHECKERS = {
    "R1": _check_r1,
    "R2": _check_r2,
    "R3": _check_r3,
    "R4": _check_r4,
    "R5": _check_r5,
}


def pre_merge_checklist(change: dict, only: list = None) -> dict:
    """
    融合前红线预检。

    参数 change 字段:
      seminar_score    float  研讨厅研判分（外部吸收必填）
      pangu_exempt     bool   盘古显式敕令豁免 R1
      diff_text/code   str    变更代码片段（用于 R2 破坏性扫描）
      is_destructive   bool   显式破坏性声明
      target           str    目标模块（R3）
      duplicates_existing str 重叠构件名（R4）
      diff_size        int    改动行数（R5）
      diff_cap         int    R5 行数阈值（默认400）
      only             list   仅检查指定红线（默认全检）

    返回: {"passed": bool, "violations": list[str], "checked": int, "details": dict}
    """
    rules = only or [r[0] for r in RED_LINES]
    violations = []
    details = {}
    for rid in rules:
        if rid not in _CHECKERS:
            continue
        passed, detail = _CHECKERS[rid](change)
        details[rid] = {"passed": passed, "detail": detail}
        if not passed:
            violations.append(f"[{rid}] {detail}")

    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "checked": len(rules),
        "details": details,
    }


if __name__ == "__main__":
    print("pre_merge_checklist 自检:")

    # 案例1: 合法融合（盘古敕令豁免 + 有落点 + 小改动）
    ok = pre_merge_checklist({
        "pangu_exempt": True,
        "target": "bridge/rrif_gate_modulator.py",
        "diff_text": "def cost_ladder(self): pass",
        "diff_size": 25,
    })
    print(" 案例1(合法):", "✅ 通过" if ok["passed"] else "⛔ 拦截", ok["violations"])

    # 案例2: 无研判分 + 硬编码 session → 拦截
    bad = pre_merge_checklist({
        "seminar_score": 0.70,
        "diff_text": "if sessionid == '58ae08b4': kill()",
        "target": "bridge/x.py",
        "diff_size": 10,
    })
    print(" 案例2(违规):", "✅ 通过" if bad["passed"] else "⛔ 拦截", bad["violations"])
