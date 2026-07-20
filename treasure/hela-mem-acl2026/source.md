# HeLa-Mem: Hebbian Learning and Associative Memory for LLM Agents

> 来源: arXiv 2604.16839 | ACL 2026 (main)  
> 代码: https://github.com/ReinerBRO/HeLa-Mem  
> 觅食时间: 2026-06-27

---

## 一、核心贡献

HeLa-Mem 提出了一种受神经科学启发的LLM Agent记忆架构，将对话历史建模为带**赫布学习动力学**的动态图。核心三个生物学机制：

1. **关联(Association)** — 赫布学习："一起激活的连在一起"
2. **巩固(Consolidation)** — 反思性蒸馏：高频记忆簇→语义知识
3. **扩散激活(Spreading Activation)** — 沿关联路径触发相关记忆

---

## 二、技术方案

### 赫布学习规则

$$w_{ij}^{(t+1)} = (1-\lambda) \cdot w_{ij}^{(t)} + \eta \cdot \mathbb{I}(v_i, v_j \in \mathcal{K}_t)$$

| 参数 | 值 | 含义 |
|:----|:--:|:----|
| η | 0.02 | 学习率(每次共激活的边权增量) |
| λ | 0.995 | 衰减率(长期不用的边逐渐消失) |
| β | 0.1 | 扩散激活强度 |
| τ | 60天 | 时间常数 |
| δhub | — | 枢纽节点阈值(蒸馏触发) |

### 双路径检索

1. **基础路径** — Top-k 语义相似度检索
2. **扩散路径** — 沿赫布强边传播激活，捕获"语义远但关联近"的记忆

### 反思性蒸馏

检测节点总边权 `D(vi) = Σwij > δhub`
→ 标记为枢纽 → 提取该节点及强连接邻居 → LLM合成语义知识 → 存入语义记忆库

---

## 三、关键实验数据

| 问题类别 | HeLa-Mem | 最强基线 | 提升 |
|:--------|:--------:|:--------:|:---:|
| 多跳F1 | 40.14 | 38.39 | +1.75 |
| 时序F1 | 47.29 | 41.58 | +5.71 |
| 开放域F1 | 29.70 | 23.75 | +5.95 |
| 单跳F1 | 51.89 | 45.86 | +6.03 |

Token效率：HeLa-Mem仅用~1,010 token，基线MemoryOS用2,000+。

### 消融实验

| 去掉 | 平均F1下降 |
|:----|:----------:|
| 反思Agent | **-4.87** (最大) |
| 扩散激活 | -2.55 |
| 自适应遗忘 | -0.46 |

---

## 四、对曦和的P0启发

HeLa-Mem直接命中了曦和最大的短板——**赫布现在是静态计数器（3079只是个数字）**。

### 曦和没有的
- 赫布动态图结构(节点+边+权重)
- 共激活→边权自动增长
- 长期不用→边权自动衰减
- 枢纽检测→驱动反思蒸馏

### 曦和已有的
- 赫布追踪器(bridge/hebbian-tracker.json)
- 反思库(memory/reflections/)
- 记忆图谱(memory/graph/)
- T4循环(可以集成赫布动态图)

### 落地路径

```
Step 1: 建HebbianGraph类(复刻+精简) → 30行代码
Step 2: T4集成(每次事件=节点，同tick=共激活)
Step 3: T5蒸馏(枢纽节点→驱动反思生成)
```

---

## 五、代码结构

```
hela_mem/
├── hebbian_memory.py        核心图结构+赫布学习
├── hebbian_knowledge_memory.py  语义记忆存储
├── hebbian_retriever.py     双路径检索
├── encode_longmemeval.py    编码入口
├── eval_longmemeval.py      评估入口
├── profile_utils.py         用户画像工具
├── reranker.py              重排序器
└── utils.py                 工具函数
```

---

*全文阅读: arXiv 2604.16839 | GitHub: ReinerBRO/HeLa-Mem*
