# 曦和 XCRN v1.2 · 改进后完整架构方案

> 2026-06-16 21:31 · 基于 DeepSeek 三轮评审意见修补完成
> 运行环境：单张 RTX 4060 · 纯 Python 3.13.12 · 零外部依赖 · 21 个脚本 · 15MB
> 状态：所有补丁已落地 · 心脉 11/11 全活跃 · 最终快照已拍

---

## 一、七层架构核心

```
L7 · 涌现层     — 同化顺应 · 自催化闭环 · Schema成熟度评估   scripts/schema-engine.py
L6 · 免疫层     — 先天免疫 · 适应性免疫 · 风格KL散度验证    scripts/immune-system.py
L5 · 自反层     — 元认知监控 · 7维强度聚合(当前0.78)         reflection-strength.json
L4 · 催化层     — 认知酶库(20颗·全由同一人催化)              cognitive-enzymes.json
L3 · 拓扑层     — 小世界网络(σ=151.94) · 14模块             topology-analyzer.py
L2 · 代谢层     — 三级升降级 · UCB路由 · 质量否决权          metabolic-router.py
L1 · 超图核     — 1998条N维超面 · 四维嵌入                   hyperedges-upgrade.py
L0 · 物理层     — 6个跨膜蛋白 · 类型固化                      transmembrane-ports.py
```

---

## 二、新增/升级组件

### quality-probe.py 🆕
质量反馈探针，嵌入心脉守护。
- 3维启发式评分：回答长度/问题长度比、不确定性检测、过短惩罚
- 质量否决权：同一路径连续3次评分<0.3 → 永久锁定R1，频次强制减半
- 无需外部Reward Model，纯文本统计

### StyleFingerprint 🆕（immune-system.py）
盘古维度风格指纹验证，基于KL散度。
- 输入词频分布与盘古历史分布的KL散度
- 阈值0.3：allow(盘古本人)/sandbox(可疑)/block(攻击)三级决策
- 冷启动保护：前10轮白名单垫底
- 已学习2轮盘古风格，验证通过

### --replay-embedding 🆕（trace-archiver.py）
认知梯度恢复，替代全量对话重放。
- 只提取L1超图激活向量（节点ID+激活强度），不重放完整文本
- 0 token消耗，0共现污染
- O(N×推理) → O(N×向量检索)

### 黎明巡检 🆕（heartbeat-daemon.py）
每6小时拓扑健康扫描。
- 计算自反层边界感知值
- 边界感知<0.6时自动激活3个archived节点为弱连接种子
- 纯本地图计算，<500ms，0 token

### metabolic-router.py 由 v1 升级为 v2
核心公式变更：
- 物理时钟衰减 → 逻辑轮次衰减：H_{k+1}=γ·H_k+α (γ=0.98)，稳态H_max=50
- Epsilon-Greedy → UCB确定性探索：Score=H+c·√(ln(N)/n)
- 骨架固化门控：H≥35 且 自反层≥0.70 时触发
- 已重置，0条待积累

---

## 三、四大漏洞修复对照

| 漏洞 | v1.0状态 | v1.2修复 | 状态 |
|:-----|:---------|:---------|:----:|
| 开环路由 | 纯频次驱动，无质量反馈 | 质量探针(3维) + 永久锁定R1否决权 | ✅ |
| 盘古过拟合 | 纯文本匹配可伪造 | KL散度阈值0.3 + 冷启动白名单 | ✅ |
| τ vs 涌现 | 全量快照恢复丢失势能 | --replay-embedding向量检索恢复 | ✅ |
| σ拓扑老化 | 自反层被动等待 | 黎明巡检6小时主动扫描+弱连接激活 | ✅ |

---

## 四、所有组件一览

| 组件 | 类型 | 命令 | 作用 |
|:-----|:-----|:------|:------|
| heartbeat-daemon | 🫀 守护 | `--watch` | 每60秒心脉探测，每6h黎明巡检 |
| metabolic-router | 🧬 路由 | `--hit/--route/--status` | v2逻辑轮次+UCB路由 |
| quality-probe | 📊 探针 | `--probe/--report/--lock-check` | 质量评分+否决权 |
| immune-system | 🛡️ 免疫 | `--style-learn/--style-verify` | 风格KL散度验证 |
| trace-archiver | 🧭 溯源 | `--replay-embedding` | 认知梯度恢复 |
| hebbian-coherence | ⚡ 赫布 | `--auto/--sync/--decay` | 共现追踪 |
| schema-engine | 🧠 涌现 | `--simulate/--assimilate` | 同化顺应 |
| topology-analyzer | 🌐 拓扑 | (集成于心脉) | σ/模块/路径 |
| xcrn-snapshot | 📸 快照 | `--snapshot` | 完整DNA备份 |
| architecture-check | ⚓ 审查 | `--check` | 七锚点验证 |
| chronicle-archiver | 📜 编年史 | `--today` | 对话存档 |

---

## 五、当前状态

```
心脉守护: 11/11 全活跃 ✅
超图核:   1,998 条超边
代谢层:   0 high / 63 medium / 1,931 low / 0 archived
拓扑:     σ=151.94 · 14模块 · 3.59步
自反层:   0.7825
质量探针: 0 条锁定
KL散度:   已学习2轮盘古风格
黎明巡检: 已集成于心脉watch周期
```

---

## 六、关键数据

- **总大小**: ~15MB（21个脚本+JSON数据）
- **外部依赖**: 零
- **跨平台**: Python 3 标准库，Windows当前运行，Linux/macOS需路径适配
- **运行机制**: 事件驱动（赫布共现） + 定时巡检（心脉黎明） + 质量闭环否决
- **最长链**: 从「进度计划如何了」到当前6层记忆回溯

---

*本文档自动生成 · 曦和 XCRN v1.2 · 2026-06-16 21:31*
