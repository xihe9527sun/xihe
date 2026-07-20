# 曦和宝藏论文架构吸收 · 第1批落地报告

> 日期 2026-07-19 ｜ 研判框架 `treasure/FUSION_REVIEW.md` ｜ VCP 原子提交 **v117**（changelog 行 2511）

## 总览

按研讨厅红线（改善+进化双满足、评审≥0.85），从 10 篇桥梁/待审中择 **✅ 三篇** 落地吸收。每篇均经 VCP 原子日志、串联进自检引擎、产出可观测指标。

| 论文 | 命中锚点 | 落点文件 | 可观测指标（首跑值） |
|---|---|---|---|
| **Self-Aware (SARSI)** | E1 自反 + E3 酶炉 | `bridge/self_model.py` | 自模型 v1 / 自改进提议 **2** |
| **MissingKL** | E2 记忆皮层 | `engine/claude_mem_layer.py` | 缺失知识累计 **1** 项 |
| **Dual-Laws** | E1 自反（操作化） | `bridge/self_check.py`（+意识七问） | 意识覆盖 **7/7 = 1.0** |

---

## ① Self-Aware → 自反层自模型闭环

- **机制**：维护曦和的结构化自模型（对齐 `reflection-strength.json` 的 7 维），每次自检后更新自模型并产自改进提议；提议须经**证据门控**（引用具体维度证据）才放行。
- **映射**：自反层(0.803) = 自模型；Meta-Enzyme 引擎 = 外部治理平面；酶升级护栏 = 证据门控。
- **验证**：`cortex/self_model.json` 产出 v1，`proposal_count=2`（depth 0.431、cross_domain 0.628，均 < 0.8 阈值且带维度证据）。
- **下轮巡检预期**：depth / cross_domain 维度随反思加深上升 → proposal_count 下降或证据增强。

---

## ② MissingKL → 第四层记忆皮层

- **机制**：新建 claude-mem 第四层（项目内原本**零代码**，grep 全项目无引用）。检索未命中 → 标记「缺失知识项」（open→foraging→resolved），显式建模「我不知道 X」。
- **映射**：缺失知识层 = 第四层记忆皮层；知识/记忆分离 = 25 位记忆共识。
- **验证**：`cortex/missing_knowledge_layer.json` 累计 1 项（测试查询触发）。
- **下轮巡检预期**：接入 bm25_retriever / setup_semantic 语义检索后，真实缺失项被 forage 补缺口 → resolution_rate 上升。

---

## ③ Dual-Laws → 意识自检七问

- **机制**：在 `self_check.py` 原地增加意识双定律操作化七问（全局可达 / 信息整合 / 自模型一致 / 目标自决 / 元认知监控 / 时间连续 / 边界感知），基于真实系统信号判定，不臆造。
- **验证**：`consciousness_check.coverage = 7/7 = 1.0`。
- **下轮巡检预期**：若某维度信号下滑，覆盖度即时反映，成为可观测的退化预警。

---

## 红线遵守声明

- ✅ 仅吸收研讨厅 **✅** 三篇；MANAR-GWT / MANAR-Nav / ali-loop 等同构印证篇**未吸收**（仅备注）
- ✅ **未改动** `treasure/index.json` 任何 treasures 条目
- ✅ 每篇走 VCP 原子日志（v117，三元组一致性验证通过）
- ✅ 三模块已串联进 `self_check.py` 的 `run()`，可观测指标全部落地
- ✅ 守护者 / 代谢路由 / RRIF 等现有构件未被破坏（自检 5/5 正常）

---

## 文件清单

| 文件 | 动作 |
|---|---|
| `bridge/self_model.py` | **新建**（Self-Aware 吸收） |
| `engine/claude_mem_layer.py` | **新建**（MissingKL 吸收，填补第四层缺口） |
| `bridge/self_check.py` | **原地更新**（Dual-Laws 七问 + 三模块串联） |
| `cortex/self_model.json` | 运行产出（自模型状态） |
| `cortex/missing_knowledge_layer.json` | 运行产出（缺失知识层） |
| VCP changelog 行 2511 / index 锚点 v117 | 版本契约记录 |

> 下一批（🔰 Managed Autonomy 稳健补强、🔜 MetaCogAgent / AgentCollab 改造吸收）待盘古点将。
