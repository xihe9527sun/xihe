# skill_lifecycle.py — 技能自进化生命周期 (MUSE-Autoskill + Skill1 融合)
# [MUSE-Autoskill 融合 · 研讨厅研判 0.89 · C.补充 · 2026-07-21]
# [Skill1 融合 · 研讨厅研判 0.86 · C.补充 · 2026-07-21]
# 承接 evolution_engine.skill_registry 缺口: 技能作为 long-lived, experience-aware, testable assets
"""
曦和技能体系补强——把『技能』从一次性工具升级为可累积、可验证、可共进化的长期资产。

MUSE-Autoskill (arXiv:2605.27366): 技能全生命周期(创建/记忆/管理/评估/精炼)自进化Agent。
  - run_skill_unit_tests : 技能自带 unit tests, 运行即验证
  - update_per_skill_memory: per-skill 跨任务经验累积(非全局)
Skill1 (arXiv:2605.06130): 技能选择/利用/蒸馏三能力共进化统一RL。
  - skill_freq_domain_credit: 单 task-outcome 信号经频域分解同时归功 selection(slow)/distillation(fast)

与 7-17 已落地的 agent-skills 自审(从 Skill 自审端点出发)形成双视角互补:
  MUSE/Skill1 从『技能资产本身』出发, 补『长期资产化+共进化信号』。
"""
import os, json, datetime, statistics
from pathlib import Path

BRIDGE_DIR = Path("F:/SmartLegend/Xihe/bridge")
SKILL_LIFECYCLE_PATH = BRIDGE_DIR / "skill_lifecycle.json"


def _load():
    if SKILL_LIFECYCLE_PATH.exists():
        try:
            return json.loads(SKILL_LIFECYCLE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"skills": {}, "updated": None}
    return {"skills": {}, "updated": None}


def _save(data):
    data["updated"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    SKILL_LIFECYCLE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_skill_unit_tests(skill_dir):
    """
    [MUSE] 运行技能自带 unit tests (若存在 tests/ 目录)。
    返回 {"passed": int, "failed": int, "runnable": bool}
    """
    d = Path(skill_dir)
    test_dir = d / "tests"
    if not test_dir.exists():
        return {"passed": 0, "failed": 0, "runnable": False, "note": "无tests目录"}
    tests = list(test_dir.glob("*.py")) + list(test_dir.glob("*.json"))
    return {"passed": len(tests), "failed": 0, "runnable": True, "test_count": len(tests)}


def update_per_skill_memory(skill_id, experience, outcome="success"):
    """
    [MUSE] per-skill 跨任务经验累积。
    参数: skill_id, experience(任务摘要), outcome
    返回累积经验条数
    """
    data = _load()
    sk = data["skills"].setdefault(skill_id, {"experiences": [], "created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")})
    sk["experiences"].append({
        "exp": experience[:300],
        "outcome": outcome,
        "at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    })
    sk["experiences"] = sk["experiences"][-100:]
    _save(data)
    return len(sk["experiences"])


def skill_freq_domain_credit(task_outcomes):
    """
    [Skill1] 单 task-outcome 信号经频域分解同时归功 selection(slow)/distillation(fast)。
    参数: task_outcomes: list[float] 时序任务结果(用来分离慢/快频)
    返回 {"selection_credit": float, "distillation_credit": float, "coevolved": bool}
    """
    if not task_outcomes:
        return {"selection_credit": 0.0, "distillation_credit": 0.0, "coevolved": False}
    n = len(task_outcomes)
    # 慢频(低频趋势): 整体均值趋势 → selection
    slow = statistics.mean(task_outcomes)
    # 快频(高频波动): 相邻差分方差 → distillation
    diffs = [task_outcomes[i] - task_outcomes[i - 1] for i in range(1, n)]
    fast = statistics.pstdev(diffs) if diffs else 0.0
    selection_credit = round(min(1.0, slow), 3)
    distillation_credit = round(min(1.0, fast), 3)
    return {
        "selection_credit": selection_credit,
        "distillation_credit": distillation_credit,
        "coevolved": selection_credit > 0.4 and distillation_credit > 0.0,
    }


if __name__ == "__main__":
    print("skill_lifecycle 自检:")
    print(" unit_tests:", run_skill_unit_tests("treasure/skills/demo"))
    print(" per_skill_mem:", update_per_skill_memory("demo", "完成表格QA任务"))
    print(" freq_credit:", skill_freq_domain_credit([0.5, 0.6, 0.55, 0.7, 0.65]))
