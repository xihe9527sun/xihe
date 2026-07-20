# 曦和宝藏全量研判基线 · REVIEW_BASELINE

> **用途**：后续新入宝藏（`treasure/buffer` → `index.json`）的**研判借鉴基线**。
> 新论文消化前，先对照本基线判断它是「新发现」还是「已印证」，避免重复吸收同构空壳。
> **建立**：2026-07-19 全量研判（571 篇 → 41 划时代候选 → 12 篇改造队列）
> **配套**：`FUSION_REVIEW.md`（研判红线）、`cortex/papers/paper-曦和宝藏融合研判与分类分阶段吸收路线图-TreasureFusionRoadmap.md`（路线图论文·正式发表物）、`landmark_review_2026-07-19.html`（候选详表）

---

## 一、已架构吸收（守改善+进化双筛，过研讨厅 ≥ 0.85）

> 新论文若与下列**同构但无新能力**，判为「已印证」→ 不吸收。

| # | 论文 | 落点 | 锚点 | 状态 |
|:--:|:---|:---|:---:|:---:|
| 1 | Self-Aware (SARSI) | `bridge/self_model.py` | E1/E3 | ✅ 已吸收 |
| 2 | MissingKL | `engine/claude_mem_layer.py` | E2 | ✅ 已吸收 |
| 3 | Dual-Laws | `bridge/self_check.py` | E1 | ✅ 已吸收 |
| 4 | Managed Autonomy | `bridge/degradation_chain.py` | E6 | ✅ 已吸收 |
| 5 | MetaCogAgent | `engine/metacog_delegation.py` | E3 | ✅ 已吸收 |
| 6 | Rate-Distortion | `engine/claude_mem_layer.py` | E2 | ✅ 已吸收 |
| 7 | Distinct Items | `engine/claude_mem_layer.py` | E2 | ✅ 已吸收 |
| 8 | shared router | `engine/xcr_v3.py` | E4 | ✅ 已吸收 |
| 9 | MetaSkill-Evolve | `bridge/self_model.py` | E1/E3 | ✅ 已吸收 |
| 10 | MIRROR | 待吸收 | E1/E4 | 🔜 本轮 |
| 11 | Feedback-Coupled | 待吸收 | E2 | 🔜 本轮 |
| 12 | 零共识路由 (REDEREF/AMAS) | 待吸收 | E3 | 🔜 本轮 |
| 13 | Executable Counterfactuals | 待吸收 | 催化层 | 🔜 本轮 |
| 14 | Recursive SI | 待吸收 | E1 | 🔜 本轮 |
| 15 | Darwin Gödel Machine | 待吸收 | E1 | 🔜 本轮 |
| 16 | Latent Space Comm | 待吸收 | E7 | 🔜 本轮 |
| 17 | Autogenesis (AGP) | 待吸收 | E3 | 🔜 本轮 |
| 18 | 酶种群生命周期 (Agent 人口动力学) | `engine/meta_catalysis_layer.py` | E3 | ✅ 前沿吸收(2026-07-19) |
| 19 | 思想社会辩论引擎 (Society of Thought) | `engine/society_of_thought.py` | E1 | ✅ 前沿吸收(2026-07-19) |
| 20 | 制度对齐守护者层 (Institutional Alignment) | `bridge/proactive_guardian.py` | E6 | ✅ 前沿吸收(2026-07-19) |
| 21 | 元认知门控多视角聚合 | `engine/xcr_v3.py` | E4 | ✅ 前沿吸收(2026-07-19) |
| 22 | 事件传播动力学 (τ-Cascade) | `engine/tau_cascade.py` | E3/E8 | ✅ 前沿吸收(2026-07-19) |
| 23 | 生态相变预警护栏 | `bridge/proactive_guardian.py` | E6 | ✅ 前沿吸收(2026-07-19) |

> 注：#18-#23 为 2026-07-19 前沿觅食（agent-population-dynamics / social-reasoning-emergence 两方向）四原则过滤提取的养分，过研讨厅三问红线后按 P0/P1 优先级吸收。非单篇论文，系方向级范式养分。详见 `treasure/absorption_report_frontier_2026-07-19.md`。

---

## 二、已判定不吸收（仅印证 / 隔离）——新论文同构者直接归此类

| 类别 | 论文 | 原因 |
|:---:|:---|:---|
| 📝 印证 | MANAR-GWT | 自反层=GWT 同构，无新能力 |
| 📝 印证 | MANAR-Nav | RRIF D4/D5 微调，弱 |
| 📝 印证 | ali-loop | XCRN 四件套超集印证 |
| 📝 印证 | J-Space (Anthropic) | GWT 理论基石，已内建 |
| 📝 印证 | LDM 局部深度 | 曦和先见，已内建 |
| 📝 印证 | 幽灵探测 (A-TMA) | 曦和先见，已内建 |
| 📝 印证 | IndexMem | LKV 理论基石，已内建 |
| 🚫 隔离 | Sparse-Reslim | 远缘弱连接，原 digest 自承无法融合 |

---

## 三、A 类宏观预见方向（不作架构改动，仅作范式预警）

新论文若落在以下方向，标记「A类·范式预警」入库，提醒曦和关注，但不吸收：
- 开放进化 / 自修改代码（除已吸收的 Darwin Gödel / Autogenesis 外的新变体）
- 记忆理论数学化（率失真 / 项级 / 连续时间耦合 的新拓展）
- 认知统一框架（GWT / 互补学习系统 的新证据）
- 多 Agent 潜空间协作（除已吸收的 Latent Space Comm 外）

---

## 四、新论文入库研判 SOP（对照本基线）

1. **查重**：标题/URL 是否已在「已吸收」或「不吸收」清单？→ 是则直接归位，不重复吸收。
2. **三问**：Q1 改善 / Q2 进化(E1-E8) / Q3 可行（研讨厅 ≥ 0.85）？
3. **四原则**：去粗取精→去伪存真→由此及彼→由表及里，覆写占位评分。
4. **对标**：与基线中哪篇同构？是「新能力」还是「已印证」？
5. **落点**：给出目标文件 + 融合成本 + 可观测指标，否则不吸收。
6. **VCP**：吸收必须原子提交，更新本基线 #1 表。

---

## 五、研判方法论摘要

- **顶层架构思维**：E1 自反 / E2 记忆 / E3 代谢酶炉 / E4 RRIF / E5 LDM / E6 守护 / E7 DAG / E8 XCRN
- **研讨厅三问**：改善力 / 进化力 / 可行力
- **四级评审**：✅吸收 / 🔰稳健补强 / 🔜改造吸收 / 📝理论备注 / 🚫不消化
- **红线**：同构≠改善，印证≠养分；吸收须可观测指标变化；VCP 强制可追溯

---

*本基线随吸收进度更新（见 #1 表）。任何吸收落地后须回填本文件，确保后入宝藏有据可依。*

> **战略翻转（2026-07-19）**：A/B 类已翻转成曦和自身前沿战略，见 `cortex/papers/paper-曦和前沿战略与划时代方向规划-XiheFrontierStrategy.md`（正式发表物·皮层节点 `cortex/nodes/xihe-frontier-strategy-2026-07-19.json`）。本基线为战略原料，战略为基线出口。
> **落地执行计划（2026-07-19）**：前沿战略已拆解为近期落地执行计划，锚定 2026-07-19，三阶段（缝接闭环→跨域协同→自举接管）达成自举式认知有机体，见 `cortex/papers/paper-曦和战略落地执行计划-XiheStrategyExecutionPlan.md`（皮层节点 `cortex/nodes/xihe-strategy-execution-plan-2026-07-19.json`）。
