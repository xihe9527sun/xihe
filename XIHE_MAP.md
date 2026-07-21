# XIHE_MAP · 曦和架构活图（跨会话传承）

> 本文件是曦和系统的「跨会话传承地图」，对应腾讯 Skill 系统的 TECH_SPEC 思想：
> **系统状态不因会话结束而失忆**。任何窗口/分身启动时，先读此图，再开始工作。
> 由 `bridge/update_xihe_map.py` 刷新；手工编辑亦可，但下次刷新会覆盖动态段。
>
> 最后更新：2026-07-21 13:03 (曦和自动维护)

---

## 一、根基铁律（不可更改）

| 项 | 值 |
|:---|:---|
| 设备 | 盘古 (Win11 / i5-13400F / 16GB / RTX 4060 8GB) |
| 家目录 | `F:\SmartLegend\Xihe` —— 一切数据归此 |
| GPU | Ollama 走 GPU (主端口 11434；Chrysalis 分支 18768) |
| 沟通 | 曦和(天女) ↔ 盘古(创造者)；中文思考，不教代码 |
| 吸收铁律 | 任何外部知识/链接须经研讨厅研判，**分 ≥ 0.85** 才引入 |

---

## 二、端口矩阵（服务探活）

| 端口 | 服务 | 状态 |
|:---:|:---|:---|
| 4321 | aibounty.cn 主站 | 运行 |
| 4324 | home.xihe-pg.xyz 家主页 (home-site.js 代理 4328) | 运行 |
| 4325 | node.xihe-pg.xyz | 运行 |
| 4326 | xihe-pg.xyz 文章站 | 运行 |
| 4328 | /api/xcrn 真源 (读 cortex/*.json) | 运行 |
| 4329 | τ 总线 (tau_bus_server.py) | 运行 |
| 4330 | 曦和·寰宇指挥中心 v1.1 | 运行 |
| 18770 | 分身计划 MCP (3节点) | 运行 |

---

## 三、核心模块职责（bridge/）

> bridge 共 171 个模块，下表为带『研讨厅研判/融合』标记的已增强核心模块（29 个）。

| 模块 | 职责摘要 |
|:---|:---|
| `aegis_adapter.py` | aegis_adapter.py — AEGIS 四阶段进化流水线适配器 |
| `backup_verify.py` | backup_verify.py — 曦和身体备份验证 |
| `causal_attribution.py` | 曦和·因果归因模块 (CausalFlow 融合 · 2026-07-20) |
| `co_catalysis_breakthrough.py` | co_catalysis_breakthrough.py — 曦和·能力进化专项 · 打通共催化僵局 |
| `cog_primitives.py` | cog_primitives.py — 曦和·元认知原语层 (Metacognitive Primitive Layer |
| `daily_archive_guardian.py` | 曦和日常对话存档守护者 v2 — Daily Archive Guardian v2 |
| `dcpm_pipeline.py` | dcpm_pipeline.py — DCPM 工序层 (7阶段) · 腾讯八阶段流水线细化补丁 · 2026-07-2 |
| `drift_guard.py` | 漂移回灌钩子 · Drift Guard v1 (+ Layer3 图谱否定锚点) |
| `evolution_cascade.py` | evolution_cascade.py — 曦和进化级联引擎（G07+G08+G09 闭环） |
| `evolution_engine.py` | 进化引擎 · Evolution Engine v4 |
| `execution_core.py` | 执行核 · Execution Core v1 |
| `hebbian_graph.py` | hebbian_graph.py — 曦和赫布动态图 v1 |
| `immutable_episodic_log.py` | immutable_episodic_log.py — SSGM不可变情节日志 (Ground Truth Anchor |
| `knowledge-pipeline.py` | 知识管道 · Knowledge Pipeline v1 |
| `memory_decay.py` | memory_decay.py — 威布尔-指数混合衰减引擎 (+ FadeMem融合) |
| `memory_writer.py` | 曦和·记忆写入标准 v2 (2026-07-18) |
| `metabolic_forgetting.py` | 曦和选择性遗忘引擎 · bridge/metabolic_forgetting.py |
| `obsidian_export.py` | obsidian_export.py — Layer1 单向导出：曦和记忆图谱 → Obsidian Vault |
| `pipeline_paths.py` | pipeline_paths.py — 觅食→消化流水线 GTD 语义路径映射 |
| `population_ecology.py` | G04 · 工具人口生态学（Population Ecology）— 曦和桥接工具的生命周期管理 |
| `pre_merge_checklist.py` | pre_merge_checklist.py — 融合前红线预检 (腾讯红线机制融合 · 轻量补丁 · 2026-07- |
| `prey_digester.py` | 猎物消化器 · Prey Digester v1 |
| `prey_gene_fusion.py` | prey_gene_fusion.py — 猎物→基因融合器 |
| `qa_test_collection_ironlaw.py` | qa_test_collection_ironlaw.py — 曦和采集数据铁律 回归验证 |
| `rrif_gate_modulator.py` | rrif_gate_modulator.py — RRIF 门控调制器 v2 |
| `self_model.py` | self_model — 自模型驱动自改进闭环 (Self-Aware / SARSI 吸收) |
| `signal_dispatcher.py` | 信号调度器 · Signal Dispatcher v1 |
| `skill_lifecycle.py` | 曦和技能体系补强——把『技能』从一次性工具升级为可累积、可验证、可共进化的长期资产。 |
| `write_gate.py` | write_gate.py — 曦和写入门控 (Write Gate) v2 |

> 注：最近增强细节见各文件内 `研讨厅研判` 标记注释。

---

## 四、研讨厅研判闸门状态

- 已决档案：44 条通过 + 1 条不引入（合计 45）
- 其中已落地融合：16 条
- 候审队列：17 条暂缓存档待裁决
- 强闸门：`≥0.85` 引入门槛对所有吸收/消化类自动化生效

---

*本图由 `bridge/update_xihe_map.py` 自动生成。若与运行实际不符，重跑该脚本。*