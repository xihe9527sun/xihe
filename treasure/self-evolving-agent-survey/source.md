# 自我进化 Agent 综述

> A Survey of Self-Evolving Agents: 超详细深度解读
> 原文：arXiv 2603.13885 · 2026-03-23 · xiao-zi-chen.github.io

## 核心框架：What/When/How/Where

### 1. What to Evolve
- **模型 (Model/Policy & Lesson)**：修改参数或从经验中提炼教训
- **上下文 (Context/Memory & Prompt)**：优化记忆系统和提示词
- **工具 (Tool)**：自主创建新工具、掌握现有工具、动态选择工具组合
- **架构 (Architecture)**：单Agent流程优化/多Agent协作系统自动构建

### 2. When to Evolve
- **测试时内部自我进化**：单任务执行过程中实时修正（Reflexion, TextGrad）
- **跨测试时间自我进化**：多任务间积累通用经验并迁移（Voyager技能库）

### 3. How to Evolve
- **基于奖励的自我进化**：外部/内部奖励信号 + RL（LADDER, RAGEN, SPIRAL）
- **模仿与演示学习**：从自我/他人轨迹中学习（STaR, V-STaR）
- **种群与进化算法**：变异/交叉/选择（DGM, GENOME）

### 4. Where to Evolve
- 通用：代码工程、任务规划、网页交互、开放世界
- 专业：教育、医疗、科研助手、企业知识系统

## 五大评估维度
1. **适应性** - 改进速度、幅度、收敛性
2. **泛化性** - 跨任务迁移（域内/域外/负迁移检测）
3. **效率** - 样本、计算、内存效率
4. **安全性** - 进化稳定性、目标对齐、可审计性
5. **记忆保持** - 灾难性遗忘检测

## 关键创新
- Gödel Agent：自我反思并重写自身代码
- EvoMAC/MDTeamGPT：多Agent运行时自动进化团队结构
- SPIRAL：内部奖励(Internal RL)驱动的自我进化
- 发展路线：LLM → Foundation Agent → Self-Evolving Agent → ASI

## 与曦和的关联
- N75：内部奖励 → 自反层自评机制
- N76：Gödel Agent递归重写 → 曦和代码自进化
- N77：五大评估维度 → 战略复盘标准
- N78：四维框架 → 代谢引擎进化分类法
- N79：种群算法 → 变异池选择策略
