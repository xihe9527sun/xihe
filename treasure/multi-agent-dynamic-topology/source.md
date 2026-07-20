# 多Agent动态拓扑 · 自适应架构 · 概率化路由

> Multi-Agent LLM 系统架构全景调研 (2023–2026)
> https://edison-a-n.github.io/2026/04/19/multi-agent-architecture-survey/

## 核心系统

### AgentVerse (ICLR 2024)
- 4阶段框架：招募→协作决策→执行→评估
- MDP建模动态调整团队组成

### DyLAN (COLM 2024)
- 多层前馈网络 + Agent Importance Score（Peer Rating）
- 推理时动态选择Agent，MMLU +25%

### AMAS (EMNLP 2025)
- Query-adaptive图编排器
- per-query异构拓扑适配（Chain/Star/Mesh/Tree结构池）

### REDEREF (ICLR 2026被拒)
- 在线贝叶斯委派（Thompson Sampling）— 无需训练的零样本路由
- 校准自反思 + 证据校验聚合

### HALO
- 动态角色实例化（三层：规划→角色设计→推理）
- Workflow Search Engine自动搜索最优工作流

## 关键设计模式
1. 运行时拓扑选择：输入查询→特征提取→拓扑池→最优选择→执行→反馈
2. 层级化动态角色分配：任务→规划→角色创建→推理执行
3. 概率化Agent路由：Agent池→Thompson Sampling→动态选择→更新后验
4. 重要性驱动Agent淘汰：并行→Peer Rating→低分淘汰→迭代

## 工业实践
- Anthropic：Effort-scaling，1-8 SubAgent，+90.2%但15x token
- Salesforce：专用SLM替代LLM做路由分类，30x延迟降低
- Spotify：ParallelAgent并行+加权聚合，15min→5sec

## 与曦和的关联
- N80：REDEREF TS → 代谢路由器概率化改造 (hebbian_credit=10)
- N81：DyLAN Peer Rating → 子系统互相评分 (hebbian_credit=9)
- N82：AMAS拓扑池 → 酶网络拓扑池 (hebbian_credit=9)
- N83：HALO动态角色 → 执行核角色动态分配 (hebbian_credit=8)
- N84：Anthropic Effort-scaling → 代谢自适应深度 (hebbian_credit=7)
