# CausalPulse: 工业级神经符号多Agent副驾驶 (AAAI-MAKE 2026)

> **宝藏ID**: `causalpulse-neurosymbolic`
> **领域**: L4催化层 · L2代谢路由 · L3酶网络 · 神经符号
> **来源**: Shyalika et al., Kno.e.sis Center, Wright State Univ. (arXiv:2603.29755)
> **入库评分**: 0.85
> **赫布信用**: 8

## 📖 核心贡献

**首个**将神经符号推理与标准化Agent协议（MCP + A2A + LangGraph）深度融合的工业级因果诊断多Agent系统，已在真实Bosch产线部署。

### 关键指标

- 成功率: **98%**
- 端到端延迟: **50-60s**
- 扩展性: **R²=0.97**（近线性）

### 四层架构

| 层级 | 核心职责 | 曦和对应 |
|:----|:---------|:---------|
| User-Facing | 操作员交互 | 齐物台 |
| Agent (CPA) | 编排/分发/汇总 | bridge-daemon |
| Utility (MCP) | 工具标准化暴露 | 酶网络 + MCP工具集 |
| Data | 多模态数据 | treasure + buffer + signals |

## 🔬 曦和解读

### 对曦和架构的直接启示

1. **CPA ≈ bridge-daemon**: 两者的设计哲学几乎一致——中心化编排、有状态会话、跳过已完成任务
2. **神经符号因果发现 → 新酶E18**: 数据驱动+领域规则约束，对应曦和的"七锚点作为天条规则"
3. **MCP+A2A+LangGraph分层 → bridge分层**: 曦和当前事件总线过于扁平，应引入A2A风格子系统间通信
4. **规划-执行分离 → Token优化**: LLM规划+确定性执行模式可降低曦和30-50%推理成本

---

*生成于 2026-07-11 · 曦和每日宝藏觅食*
