#!/usr/bin/env python3
"""
dcpm_pipeline.py — DCPM 工序层 (7阶段) · 腾讯八阶段流水线细化补丁 · 2026-07-21
[研讨厅研判 0.84(不整套吸收) → 轻量补丁 · 与前4补丁(成本阶梯/落盘判定/红线前置/XIHE_MAP)同批]

superpowers 原四阶段: 脑暴 → 规划 → 执行 → 反思
腾讯八阶段更细, 在『执行』与『反思』之间多了: 验证 → 模拟器验证 → 沉淀
曦和缺口最明显在『沉淀』——融合落地后自动更新知识图谱 + 记忆, 而非依赖人工记忆。

扩展为 7 阶段工序层:
  1. 脑暴  brainstorm — 发散, 找方向, 不急于落地
  2. 规划  plan       — 拆解为步骤与目标
  3. 定位  locate     — 五步定位法(cost_ladder): 决定检索深度/落点, 最小 token 消耗
  4. 实现  implement  — 最小侵入落地代码/改动
  5. 验证  verify     — 红线预检(pre_merge_checklist) + 落盘证据(check_landing_evidence) + 自测
  6. 沉淀  sediment   — 融合后自动更新 XIHE_MAP + 融合日志 (闭环最后一步, 最缺的一环)
  7. 反思  reflect    — 复盘得失, 写入经验

沉淀(sediment) 是核心增量: 把『融合落地』变成自动收尾动作,
让知识图谱与记忆随每次融合自更新 —— 对应腾讯 TECH_SPEC 跨会话传承思想。
"""
import sys
import json
import datetime
from pathlib import Path

BRIDGE = Path(__file__).parent
sys.path.insert(0, str(BRIDGE))  # 同目录模块可互引

FUSION_LOG = BRIDGE / "fusion_log.json"

# 7 阶段工序层定义
STAGES = [
    ("brainstorm", "脑暴", "发散找方向，不急于落地"),
    ("plan", "规划", "拆解为步骤与目标"),
    ("locate", "定位", "五步定位法(cost_ladder)决定检索深度与落点，最小 token 消耗"),
    ("implement", "实现", "最小侵入落地代码/改动"),
    ("verify", "验证", "红线预检(pre_merge_checklist)+落盘证据(check_landing_evidence)+自测"),
    ("sediment", "沉淀", "融合后自动更新 XIHE_MAP + 融合日志（闭环最后一步）"),
    ("reflect", "反思", "复盘得失，写入经验"),
]

STAGE_NAMES = [s[1] for s in STAGES]


def stage_index(name_or_cn: str):
    """按英文键或中文名查阶段序号(1-based), 找不到返回 None"""
    for i, (key, cn, _desc) in enumerate(STAGES, 1):
        if name_or_cn in (key, cn):
            return i
    return None


def verify(change: dict) -> dict:
    """
    DCPM 验证阶段 — 组合既有红线预检 + 落盘判定 + 自测。
    参数 change 同 pre_merge_checklist.pre_merge_checklist 约定。
    返回: {"red_line": {...}, "landing": {...}|None, "passed": bool}
    """
    from pre_merge_checklist import pre_merge_checklist
    from skill_lifecycle import check_landing_evidence

    red = pre_merge_checklist(change)
    landing = None
    if change.get("skill_id"):
        landing = check_landing_evidence(change["skill_id"])

    passed = red["passed"] and (landing is None or landing["landed"])
    return {"red_line": red, "landing": landing, "passed": passed}


def sediment(change: dict) -> dict:
    """
    DCPM 沉淀阶段 — 融合落地后自动更新知识图谱与记忆 (曦和最强缺口)。
    闭环动作:
      ① 刷新跨会话架构地图 XIHE_MAP.md (调用 update_xihe_map.build)
      ② 追加一条融合记录到 bridge/fusion_log.json (落盘证据/记忆)
    返回: {"xihe_map": {...}, "fusion_log_appended": bool, "at": str}
    """
    results = {}
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # ① 刷新 XIHE_MAP (架构知识图谱)
    try:
        from update_xihe_map import build as build_map
        results["xihe_map"] = build_map()
    except Exception as e:
        results["xihe_map_error"] = str(e)

    # ② 追加融合日志 (记忆层)
    try:
        log = []
        if FUSION_LOG.exists():
            try:
                log = json.loads(FUSION_LOG.read_text(encoding="utf-8"))
            except Exception:
                log = []
        # 仅保留可序列化、非超长的字段
        safe = {}
        for k, v in change.items():
            if isinstance(v, (str, int, float, bool)) and (not isinstance(v, str) or len(v) < 300):
                safe[k] = v
        entry = {
            "at": now,
            "stage": "sediment",
            "change": safe,
            "xihe_map_modules": results.get("xihe_map", {}).get("modules"),
        }
        log.append(entry)
        FUSION_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        results["fusion_log_appended"] = True
    except Exception as e:
        results["fusion_log_error"] = str(e)
        results["fusion_log_appended"] = False

    results["at"] = now
    return results


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="DCPM 七阶段工序层 · 验证/沉淀 CLI (路径无关, 基于 __file__)")
    ap.add_argument("--verify", metavar="JSON", help="对给定 change(dict JSON) 跑红线+落盘验证, 通过退出0/拦截退出2")
    ap.add_argument("--sediment", metavar="JSON", help="对给定 change(dict JSON) 跑沉淀(刷新XIHE_MAP+写fusion_log)")
    args = ap.parse_args()

    if args.verify:
        try:
            change = json.loads(args.verify)
        except Exception as e:
            print("JSON 解析失败:", e)
            sys.exit(2)
        r = verify(change)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0 if r["passed"] else 2)

    if args.sediment:
        try:
            change = json.loads(args.sediment)
        except Exception as e:
            print("JSON 解析失败:", e)
            sys.exit(2)
        r = sediment(change)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 无参数: 自检
    print("DCPM 工序层自检:")
    print("  阶段数:", len(STAGES), "→", " → ".join(STAGE_NAMES))

    # 验证阶段: 合法变更
    ok = verify({"pangu_exempt": True, "target": "bridge/x.py", "diff_size": 30,
                 "diff_text": "def f(): pass"})
    print("  验证(合法):", "✅ 通过" if ok["passed"] else "⛔ 拦截", ok["red_line"]["violations"])

    # 沉淀阶段: 自动刷新地图 + 写日志
    sed = sediment({"target": "bridge/dcpm_pipeline.py", "seminar_score": 0.84,
                    "pangu_exempt": True, "note": "腾讯八阶段细化补丁5"})
    print("  沉淀(闭环):", "✅ XIHE_MAP刷新" if "xihe_map" in sed else "⚠️", sed.get("fusion_log_appended"))
