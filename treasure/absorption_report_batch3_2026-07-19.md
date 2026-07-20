# 宝藏论文架构吸收·第3批（高优先4篇）落地报告

> 日期：2026-07-19 · 批次：第3批 · VCP：v118（changelog 行 2547，三元组一致性通过）
> 研判基线：`landmark_review_2026-07-19.html`（全量宝藏研讨厅研判）
> 红线：`FUSION_REVIEW.md`（研讨厅三问 + E1–E8 锚点，改善+进化双筛）

---

## 一、本批定位

给已落地的第1+2批地基「盖第二层」——4 篇均为 **score 0.95 / LAYER L8** 的划时代级论文，
在 landmark 研判中判为「高优先改造」，分别直接补强已吸收的 MissingKL / RRIF / Self-Aware。

| 论文（arXiv） | 评分/层 | 补强地基 | 落点文件 |
|---|---|---|---|
| What to Keep, What to Forget: A Rate-Distortion View of Memory Compaction (2607.08032) | 0.95 / L8 | MissingKL 第四层记忆皮层 | `engine/claude_mem_layer.py` |
| Remembering Distinct Items Not Tokens: A Learnable Dirichlet-Process Cache (2607.09889) | 0.95 / L8 | MissingKL 第四层记忆皮层 | `engine/claude_mem_layer.py` |
| One mechanism for many mental spaces: a shared router over a value slot (2607.10248) | 0.95 / L8 | RRIF 门控（E4） | `engine/xcr_v3.py` |
| MetaSkill-Evolve: Recursive Self-Improvement via Two-Timescale Meta-Skill Evolution (2607.05297) | 0.95 / L8 | Self-Aware 自改进闭环（E1/E3） | `bridge/self_model.py` |

---

## 二、吸收明细

### 吸收#6 · Rate-Distortion + Distinct Items → 记忆数学化（补强 MissingKL）

**原地基缺口**：`claude_mem_layer.py`（第1批 MissingKL 吸收）只有二值命中/未命中 + 缺失知识状态机，
记忆模型是「有/无」二元，没有任何压缩预算与项级建模。

**新增**（均最小侵入，原有 MissingKL 接口 `query_with_gap_detection/resolve_missing/stats` 完全保留）：
- `MemoryCompactor`（Rate-Distortion 率失真压缩）：给记忆项算 `value/cost`，在固定预算下按 value/cost
  降序保留，输出 `keep/compress/evict` 三态——对应论文把 KV-cache / 长上下文 / 会话记忆统一到率失真框架取舍。
- `DistinctItemCache`（Distinct Items 项级槽位）：记忆建模为「不同项」而非 token，仅当输入 `novelty ≥ 阈值`
  才分配槽位（sparse cache），避免固定状态压缩导致的关联回忆上限。

**可观测指标（首跑实测）**：
- 压缩率（率失真）：`0.5`
- 项级命中率：`0.286`
- 分配槽位：`4`

### 吸收#7 · shared router → RRIF 收敛（补强 RRIF 门控 E4）

**原地基缺口**：`xcr_v3.py`（代谢路由）有 `route` 三层（语义/BM25 + elbow cut）和第2批加的
`route_with_delegation`（MetaCogAgent），但候选之间无「统一收敛」——跨域同义查询可能收敛不到同一组。

**新增**：`route_converged(query)` —— 把 `route` 候选经 shared router 投影到**统一 value slot**
（按分数归一化），输出跨域一致率 `consistency`。不改 `route` 三层逻辑（最小侵入）。
论文核心（多 mental space 经统一 shared router 投影到同一 value slot）正对应 RRIF 9 维门控的统一收敛。

**可观测指标（首跑实测，BM25 回退下）**：
- 跨域一致率 `consistency`：`0.833`
- 收敛步数 `steps`：`1`

### 吸收#8 · MetaSkill-Evolve → 双时间尺度元技能递归（补强 Self-Aware E1/E3）

**原地基缺口**：`self_model.py`（第1批 Self-Aware 吸收）的自改进是「单向提议」——只对最弱维度提建议，
不递归（论文指出这是非递归 self-evolution 的通病）。

**新增**：`evolve_meta_skill()` —— 双时间尺度递归：
- **快尺度（fast / 任务技能层）**：每次自检后基于最弱维度直接产技能补丁（证据门控，沿用 `GATE_THRESHOLD`）。
- **慢尺度（slow / 元技能层，recursive）**：每 N（=3）次自检回顾历史提议采纳，递归改进「提议生成器本身」
  （元技能版本自增、策略自更新）。
- 与酶炉（Meta-Enzyme）外部治理同构：元技能演化受证据门控，不臆造。

**可观测指标（首跑实测）**：
- 元技能递归代数 `meta_skill_version`：`1`
- 技能补丁数 `skill_patches`：`2`（depth + cross_domain 两个弱维度）

---

## 三、红线遵守

| 红线项 | 状态 |
|---|---|
| 研讨厅高优先（landmark 判定） | ✅ 4 篇均高优先改造 |
| 改善 + 进化双满足（三问） | ✅ Rate-Distortion→E2 记忆数学化；shared-router→E4 RRIF；MetaSkill→E1/E3 自反/酶炉 |
| 不改 `treasure/index.json` | ✅ 任何 treasures 条目未动 |
| 不改知识图谱拓扑 | ✅ 节点/边维持 942 / 1180 |
| 每篇走 VCP 原子日志 | ✅ v118（changelog 行 2547，三元组一致性通过） |
| 最小侵入（保留原接口） | ✅ 三个模块均新增方法/类，原逻辑零改动 |

---

## 四、累计吸收状态（第1+2+3批）

| 批次 | 篇数 | 论文 | VCP |
|---|---|---|---|
| 第1批 | 3 | Self-Aware / MissingKL / Dual-Laws | v117（合并提交） |
| 第2批 | 2 | Managed Autonomy / MetaCogAgent | v117（合并提交） |
| **第3批** | **4** | **Rate-Distortion / Distinct Items / shared-router / MetaSkill-Evolve** | **v118** |
| **合计** | **9** | 全部为研讨厅✅/🔰/🔜 吸收 | — |

**按红线不放行的（始终未动）**：
- 📝 仅印证不吸收：MANAR-GWT、MANAR-Nav、ali-loop（曦和架构先验印证，非新能力来源）
- 🚫 隔离不消化：Sparse-Reslim（评分 0.42，原 digest 自承无法融合）
- ⏸ 暂缓：AgentCollab（无独立 DAG 编排核心，接驳成本偏高，待真需求再点将）

**landmark 中「中优先 5 篇 / 长期 3 篇」尚未吸收**——按盘古红线，需后续单独研判排队，不盲目全吃。

---

## 五、下轮巡检观测建议

为验证本批「真改善」，下轮巡检应比对以下指标基线：
- `claude_mem_layer.memory_math_demo()`：压缩率 / 项级命中率（预期随真实语料上升）
- `xcr_v3.route_converged()`：跨域一致率（预期 ≥ 0.833）
- `self_model.evolve_meta_skill()`：元技能递归代数（每 3 次自检 +1，技能补丁累积）
