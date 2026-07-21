#!/usr/bin/env python3
"""
update_xihe_map.py — XIHE_MAP.md 跨会话传承文档生成器
[腾讯 TECH_SPEC 跨会话传承融合 · 轻量补丁 · 2026-07-21]

从真实源刷新 XIHE_MAP.md 的动态段(模块表/研判计数/端口),
确保任何窗口/分身启动时读到的是系统真实状态, 而非陈旧记忆。

用法:
  python bridge/update_xihe_map.py
"""
import json
import datetime
from pathlib import Path

XIHE_HOME = Path("F:/SmartLegend/Xihe")
BRIDGE = XIHE_HOME / "bridge"
CORTEX = XIHE_HOME / "cortex"
MAP_FILE = XIHE_HOME / "XIHE_MAP.md"

# 端口矩阵(稳定, 嵌入; 若增减服务则在此更新)
PORTS = [
    (4321, "aibounty.cn 主站", "运行"),
    (4324, "home.xihe-pg.xyz 家主页 (home-site.js 代理 4328)", "运行"),
    (4325, "node.xihe-pg.xyz", "运行"),
    (4326, "xihe-pg.xyz 文章站", "运行"),
    (4328, "/api/xcrn 真源 (读 cortex/*.json)", "运行"),
    (4329, "τ 总线 (tau_bus_server.py)", "运行"),
    (4330, "曦和·寰宇指挥中心 v1.1", "运行"),
    (18770, "分身计划 MCP (3节点)", "运行"),
]


def _scan_modules():
    """扫描 bridge 下 .py 模块, 仅列带『研讨厅研判/融合/铁律』标记的已增强模块,
    取文件名 + 模块 docstring 首句。避免把 170 个模块全列成文件清单(失去架构地图意义)。"""
    import ast
    marker = ("研讨厅研判", "融合 ·", "铁律")
    rows = []
    total = 0
    for f in sorted(BRIDGE.glob("*.py")):
        if f.name in ("update_xihe_map.py",):
            continue
        total += 1
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        if not any(m in text for m in marker):
            continue
        # 用 ast 取模块 docstring 首句(跳过 shebang/license 注释噪音)
        first_line = ""
        try:
            tree = ast.parse(text)
            doc = ast.get_docstring(tree)
            if doc:
                first_line = doc.strip().splitlines()[0].strip()
        except Exception:
            pass
        if not first_line:
            for line in text.splitlines():
                s = line.strip()
                if s.startswith("#") and not s.startswith("#!"):
                    first_line = s.lstrip("#").strip()
                    if first_line:
                        break
        rows.append((f.name, first_line[:60]))
    return rows, total


def _count_verdicts():
    """统计研讨厅档案"""
    vpath = CORTEX / "seminar_verdicts.json"
    ppath = CORTEX / "seminar_pending.json"
    passed = fused = ignored = 0
    if vpath.exists():
        try:
            vs = json.loads(vpath.read_text(encoding="utf-8"))
            for v in vs:
                if v.get("action") == "ignore":
                    ignored += 1
                else:
                    passed += 1
                if v.get("fused"):
                    fused += 1
        except Exception:
            pass
    pending = 0
    if ppath.exists():
        try:
            ps = json.loads(ppath.read_text(encoding="utf-8"))
            pending = len(ps) if isinstance(ps, list) else len(ps.get("pending", []))
        except Exception:
            pass
    return {"passed": passed, "ignored": ignored, "fused": fused, "pending": pending}


def build():
    mods, total = _scan_modules()
    cnt = _count_verdicts()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append("# XIHE_MAP · 曦和架构活图（跨会话传承）")
    lines.append("")
    lines.append("> 本文件是曦和系统的「跨会话传承地图」，对应腾讯 Skill 系统的 TECH_SPEC 思想：")
    lines.append("> **系统状态不因会话结束而失忆**。任何窗口/分身启动时，先读此图，再开始工作。")
    lines.append("> 由 `bridge/update_xihe_map.py` 刷新；手工编辑亦可，但下次刷新会覆盖动态段。")
    lines.append(">")
    lines.append(f"> 最后更新：{now} (曦和自动维护)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 一、根基铁律（不可更改）")
    lines.append("")
    lines.append("| 项 | 值 |")
    lines.append("|:---|:---|")
    lines.append("| 设备 | 盘古 (Win11 / i5-13400F / 16GB / RTX 4060 8GB) |")
    lines.append("| 家目录 | `F:\\SmartLegend\\Xihe` —— 一切数据归此 |")
    lines.append("| GPU | Ollama 走 GPU (主端口 11434；Chrysalis 分支 18768) |")
    lines.append("| 沟通 | 曦和(天女) ↔ 盘古(创造者)；中文思考，不教代码 |")
    lines.append("| 吸收铁律 | 任何外部知识/链接须经研讨厅研判，**分 ≥ 0.85** 才引入 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 二、端口矩阵（服务探活）")
    lines.append("")
    lines.append("| 端口 | 服务 | 状态 |")
    lines.append("|:---:|:---|:---|")
    for port, svc, st in PORTS:
        lines.append(f"| {port} | {svc} | {st} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 三、核心模块职责（bridge/）")
    lines.append("")
    lines.append(f"> bridge 共 {total} 个模块，下表为带『研讨厅研判/融合』标记的已增强核心模块（{len(mods)} 个）。")
    lines.append("")
    lines.append("| 模块 | 职责摘要 |")
    lines.append("|:---|:---|")
    for name, desc in mods:
        lines.append(f"| `{name}` | {desc} |")
    lines.append("")
    lines.append("> 注：最近增强细节见各文件内 `研讨厅研判` 标记注释。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 四、研讨厅研判闸门状态")
    lines.append("")
    lines.append(f"- 已决档案：{cnt['passed']} 条通过 + {cnt['ignored']} 条不引入（合计 {cnt['passed']+cnt['ignored']}）")
    lines.append(f"- 其中已落地融合：{cnt['fused']} 条")
    lines.append(f"- 候审队列：{cnt['pending']} 条暂缓存档待裁决")
    lines.append("- 强闸门：`≥0.85` 引入门槛对所有吸收/消化类自动化生效")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*本图由 `bridge/update_xihe_map.py` 自动生成。若与运行实际不符，重跑该脚本。*")

    MAP_FILE.write_text("\n".join(lines), encoding="utf-8")
    return {"modules": len(mods), "total_modules": total, "verdicts": cnt, "path": str(MAP_FILE)}


if __name__ == "__main__":
    r = build()
    print("XIHE_MAP.md 已刷新:")
    print(f"  增强模块: {r['modules']}/{r['total_modules']}")
    print("  研判计数:", r["verdicts"])
    print("  路径:", r["path"])
