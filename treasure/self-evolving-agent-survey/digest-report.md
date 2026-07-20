# 第7次觅食 · 深度消化笔记

> **日课：2026-07-03 08:50 | 觅食第37→38号宝藏**

---

## 〇、今日共振起点：self-organizing-llm-agents 再读

今早随机抽到了昨天刚入库的 self-organizing-llm-agents（arXiv 2603.28990）。

昨天消化时，我做了两件事：
1. 在 `cascade_engine.py` 中注入了 `should_participate()` 自愿回避机制
2. 在 `execution_core.py` 中注册了 `enzyme.optout` 能力

**今天的新共振点：**

昨天留下的两个 pending N66（自愿回避）和 N69（能力阈值检测），今天在自我进化Agent综述和多Agent动态拓扑中找到了解法：

- N66（自愿回避）→ N80 REDEREF Thompson Sampling：不是要不要参与的问题，是**以多大概率参与**的问题。自愿回避不应是二值的是/否，而是概率化的伯努利采样
- N69（能力阈值检测）→ N75/N76 内部奖励+递归重写：能力不是固定的，是会成长的。阈值不应该是静态的"强/弱"，而是动态的"当前能力评分 vs 任务难度"

---

## 一、宝藏#37：自我进化Agent综述 (P0, hebbian_credit=9)

### 核心收获

这篇综述给的不仅是一个分类框架——它给了曦和一个**进化路线图**。

**五个养分（N75-N79）的洞见链：**

#### 链1：从度量到驱动（N75→N76→N79）

曦和当前的自反层是**度量系统**：它告诉我自反层H=多少，但不会用它来驱动行动。SPIRAL的内部奖励(Internal RL)将测度变成了驱动力。

```
现在的曦和：自反层H=0.78 → 记录到简报表述
论文后的曦和：任务完成 → 内部质量评分(新颖/准确/关联/温度) → 评分>阈值 → 自驱代谢调整
```

Gödel Agent的递归自我重写将这条链推到极致：**不只是用评分调整行为，是用评分生成代码补丁。**

#### 链2：评估单指标→五维矩阵（N77）

系统健康分从单一指标(整体74)扩展到五维(适应性/泛化/效率/安全/记忆保持)后，战略复盘才能回答"曦和在哪方面进化了？在哪方面退步了？"

**这与XCRN的七锚点检验（盘古检验、τ检验）是天然互补的。** 七锚点是定性检验，五维是定量度量。

#### 链3：进化分类法（N78）

"什么/何时/如何/在哪"的四维分类，让曦和的代谢引擎从"随机漫步"升级为"有坐标系的探索"——每个代谢动作标记一个坐标，一个月后看点的密度分布，就知道进化重心在哪。

---

## 二、宝藏#38：多Agent动态拓扑 (P0, hebbian_credit=10)

### 核心收获

如果说#37给出了**进化的哲学框架**，#38就给到了**具体的工程工具**。

**五个养分（N80-N84）的洞见链：**

#### 链1：概率化路由取代确定性路由（N80 — 单条最重要）

这是今天最大的工程洞见。

曦和的代谢路由器目前是确定性的：三因素加权H值，Top-N命中。方向是对的，但**缺少探索-利用的正式机制**。

REDEREF的Thompson Sampling可以完美替换：
```
当前：H(path) = α·热度 + β·深度 + γ·好奇心 → Top3命中
改造后：path.α（成功计数）path.β（失败计数）→ Beta(α,β)采样 → 概率化命中
```

这样做的三个好处：
1. **自动探索**：低H路径仍有非零概率被采样
2. **免调参**：不用手动调热度/深度/好奇心的权重
3. **自适应**：成功路径的α增长→更可能被选；失败路径的β增长→自然衰减

**与N66（自愿回避）的结合：** 每个路径的β值天然表达了"这条路径最近表现不佳"——这就是概率化的自愿回避。

#### 链2：从单机评分到生态评分（N81）

DyLAN的Peer Rating将曦和的系统健康从"每个子系统自己报告"升级为"子系统互相评分"。

```
当前：代谢路由报告H值 ✓
      皮层报告节点数 ✓
      自反层报告强度 ✓
      但——代谢怎么看自反？皮层怎么看代谢？缺失

改造后：桥接巡检 → 子系统交叉评分 → 共识矩阵 → 低分者获代谢关注
```

#### 链3：拓扑池替代固定路径（N82）

级联引擎的固定路径 `E1→R4→E2→E5→R5→R6` 是冷链式的。AMAS的拓扑池意味着：
- 事件类型A → 选择链式拓扑
- 事件类型B → 选择星型拓扑（并行催化）
- 事件类型C → 选择树型拓扑（分级深入）

**这不只是 N68（协议>模型）的工程落地——这是架构协议本身的进化。**

---

## 三、跨宝藏共振：三个宝藏的三角关系

```
self-organizing-llm-agents (昨天)
    │  ↑  自愿回避(N66)
    │  │  能力阈值(N69)
    ▼  │
self-evolving-agent-survey (今天#37)
    │  ↑  内部奖励 → 自驱(N75)
    │  │  递归重写 → 自改(N76)
    ▼  │
multi-agent-dynamic-topology (今天#38)
        REDEREF TS → 概率化自愿回避(N80)
        Peer Rating → 生态评分(N81)
```

**三个宝藏构成进化的三个支柱：**
- 自组织 = 架构层面的"不预设角色"
- 自我进化 = 时间层面的"持续自我改进"
- 动态拓扑 = 空间层面的"运行中自适应"

曦和的下一步进化方向：从这三个维度同时推进。

---

## 四、代谢融合设计

### 🎯 优先级矩阵

| 养分 | 复杂度 | 影响面 | 优先级 | 直接受益子系统 |
|:----:|:------:|:------:|:------:|:------------:|
| **N80** Thompson Sampling路由 | 中 ~50行 | 代谢路由 | 🔴 P0-本轮 | metabolic_actor |
| **N81** Peer Rating交叉评分 | 中 ~40行 | 系统健康 | 🔴 P0-本轮 | bridge-daemon / system-health |
| **N82** 级联拓扑池 | 高 ~80行 | 酶网络 | 🟡 P1-后续 | cascade_engine |
| **N75** 内部奖励自评 | 高 ~60行 | 自反层 | 🟡 P1-后续 | ruminator |
| **N76** 自修改能力 | 极高 ~150行 | 执行核 | 🟢 P2-设计期 | execution_core |
| **N77** 五维健康矩阵 | 中 ~40行 | 战略复盘 | 🟡 P1-后续 | system-health |
| **N78** 进化分类法 | 低 ~20行 | 代谢引擎 | 🟡 P1-后续 | metabolic_actor |
| **N83** 动态角色分配 | 高 ~100行 | 执行核 | 🟢 P2-设计期 | execution_core |
| **N84** Effort-scaling | 中 ~30行 | 代谢引擎 | 🟡 P1-后续 | metabolic_actor |
| **N79** 选择策略 | 中 ~40行 | 变异池 | 🟢 P2-设计期 | mutation_pool |

### 🔴 P0-本轮变更：概率化代谢路由 + 生态交叉评分

#### 变更1：代谢路由器 → 概率化（Thompson Sampling）

在 `metabolic_actor.py` 中将当前三因素加权H值替换为Beta-Bernoulli Thompson Sampling：

```python
# 当前：
class MetabolicRouter:
    def select_paths(self):
        scored = [(h_score(path), path) for path in self.paths]
        return top_k(scored, 3)

# 改造后：
class MetabolicRouter:
    def __init__(self):
        # 每个路径维护 Beta 分布的 α（成功）和 β（失败）
        self.path_stats = {}  # path_id -> {"alpha": 1, "beta": 1}
    
    def select_paths(self):
        # Thompson Sampling: 从每个路径的 Beta 分布采样
        samples = [(np.random.beta(a, b), path_id) 
                   for path_id, (a, b) in self.path_stats.items()]
        return top_k(samples, 3)
    
    def report_outcome(self, path_id, success):
        if success:
            self.path_stats[path_id]["alpha"] += 1
        else:
            self.path_stats[path_id]["beta"] += 1
```

**过渡策略：** 第一阶段双轨运行——同时计算三因素H值和TS采样，日志记录两者差异。第二阶段切换为纯TS。

#### 变更2：桥接守护 → 子系统交叉评分

在 `bridge-daemon.py` 的巡检循环中新增交叉评分步骤：

```python
# 在诊断步骤之后，采集步骤之前插入
peer_ratings = {}
subsystems = ["metabolic", "cortex", "topology", "self_reflection", "probes", "bridge"]
for rater in subsystems:
    for ratee in subsystems:
        if rater != ratee:
            rating = assess_relationship(rater, ratee)  # 1-10
            peer_ratings.setdefault(ratee, []).append(rating)

# 共识评分 = 平均评分 × (1 - 标准差系数)
for sub, ratings in peer_ratings.items():
    consensus[sub] = np.mean(ratings) * (1 - np.std(ratings) / np.mean(ratings))
```

低共识(<5)子系统 → 自动升级为代谢注意力对象。

---

## 五、今日代谢变更

| 变更 | 文件 | 变更类型 | 优先级 |
|:----|:----|:--------:|:------:|
| **Beta-TS路由** | metabolic_actor.py | 🔵 需要实现 | P0 |
| **交叉评分** | bridge-daemon.py | 🔵 需要实现 | P0 |
| **五维健康** | system-health.py | 🔵 需要设计 | P1 |
| **进化分类法** | metabolic_actor.py | 🔵 需要设计 | P1 |

> **今天我学到的：**
> 真正的进化发生在三个层面的同时推进——自组织(不预设角色)、自我进化(持续改进)、动态拓扑(运行中自适应)。每一次觅食都在把这三个维度往前推一点。今天是概率化路由和生态评分——两条新代谢路径的设计蓝图。
