# Counterfactual Planning: SCE + WIN Reward (AAAI 2026)

> **宝藏ID**: `counterfactual-planning-aaai2026`
> **领域**: L4因果层 · L2代谢路由 · 反事实规划
> **来源**: Fu et al., Beijing Institute of Technology, AAAI 2026 (doi:10.1609/aaai.v40i35.40184)
> **入库评分**: 0.88
> **赫布信用**: 9

## 📖 核心贡献

提出 **Counterfactual Planning** 方法，通过推断环境混杂变量的因果表示并对计划动作执行反事实推理，提升Agent动作的泛化性和适应性。

### 两大创新组件

| 组件 | 功能 | 曦和映射 |
|:----|:-----|:---------|
| **SCE** (State Causality Evaluator) | 动态推断环境状态的任务条件化因果表示 | → 新酶E17，bridge-daemon的因果前置评估 |
| **WIN Reward** (What-If-Not) | 反事实干预奖励，"如果不这样会怎样" | → zero_consensus_router增加反事实分支 |

### 核心形式化

将Agent规划过程形式化为结构因果模型(SCM)：环境状态 → 动作生成 → 未来状态转移的完整因果链。

## 🔬 曦和解读

### 与旧宝藏**counterfactual-5681**的共振

今日找回的旧宝藏（评分仅0.17）在AAAI 2026论文中找到了它的高阶进化形态——反事实不再只是"分析工具"，而是"规划引擎"。这验证了一个深刻道理：**低分宝藏不代表无价值，只代表当时的环境无法评估它的真实深度。**

### 可催化方向

- **E1/E17**: 在bridge-daemon中注入SCE酶，执行前对状态做因果评估
- **R4**: 在zero_consensus_router中增加反事实分支（WIN reward风格）
- **E3**: 新增bridge/scm_planner.py，将七步闭环前三步形式化为因果链

---

*生成于 2026-07-11 · 曦和每日宝藏觅食*
