# XCRN\_架构审计\_落地

# XCRN 架构审计与落地方案

## 兼容性评估结果

| **专家方案**              | **与曦和架构兼容性** | **原因**                  |
| --------------------- | ------------ | ----------------------- |
| SurpriseDetector      | ✅ 直接可用       | 零依赖，轻量，可接入预测误差          |
| 语义对立关键词               | ✅ 已集成        | 15对关键词，不增加系统负担          |
| sentence-transformers | ⚠️ 需评估       | 80MB模型+GPU竞争，影响Ollama推理 |
| NLI零样本(bart-large)    | ❌ 太重         | 1.6GB，与响应速度优先原则冲突       |
| LangChain辩论           | ❌ 架构不匹配      | 曦和本身就是LLM，不需外部LLM扮演双角色  |
| OpenNARS推理系统          | ❌ 架构不匹配      | 完整推理系统，太重，与轻量哲学冲突       |
| 资格迹信用分配               | ⚠️ 需改造       | RL概念，曦和不是典型RL系统，需适配     |

***

## 问题一：SurpriseDetector 触发后的输出接口设计

### 设计意图

惊奇事件是**认知资源的紧急调度信号**，不应仅做日志记录。输出触发三级级联：

#### 第一级（必选）：注意力权重临时上调

接口输出：

```python
{
  "type": "ATTENTION_BOOST",
  "target_id": prey.id,
  "factor": min(3.0, surprise / threshold),
  "duration_ticks": 10   # 心跳周期
}
```

效果：对应猎物的权重在指定周期内倍乘，模拟生物本能转向。

#### 第二级（推荐）：主动发起“反思快照”

生成一条内部观察作为迷你内部猎物，快速消化（跳过冲突检测，避免递归过深）。

\{

"type": "REFLECTION\_SNAPSHOT",

"content": "维度X出现异常跃升，Δ=0.017，远超预期。可能原因：猎物Y的特征Z与历史模式显著不同。",

"source\_prey\_id": prey.id,

"priority": "HIGH"

}

此内容作为 `internal_prey` 直接送入消化器。

#### 第三级（可选）：触发预测模型局部重置

连续3次同一维度出现惊奇时触发：

\{

"type": "MODEL\_RESET",

"dimension": "depth",

"reason": "连续异常误差超出阈值，预测器失效"

}

仅重置该维度预测器参数，不影响全局。

### 实现方式

采用**回调注册表**模式：

class SurpriseManager:

def **init**(self):

self.callbacks = \[]

def register(self, callback, priority):

self.callbacks.append((priority, callback))

self.callbacks.sort(reverse=True)

def trigger(self, surprise\_event):

for \_, cb in self.callbacks:

cb(surprise\_event)

## 问题二：轻量级语义矛盾检测替代方案

### 方案A（推荐）：利用本地Ollama API零样本判断

使用已有的 DeepSeek V4 服务，无额外模型加载，延迟百毫秒级。

import requests

def detect\_contradiction\_ollama(old\_statement, new\_statement):

prompt = f"""你是一个语义矛盾检测器。给定旧认知和新陈述，仅输出一个词：

* "矛盾" 如果两者在核心事实上冲突
* "蕴含" 如果新陈述可以从旧认知合理推得
* "中立" 如果两者相关但不冲突

不要解释，只要标签。

旧认知：\{old\_statement}

新陈述：\{new\_statement}

标签："""

response = requests.post(

"[http://localhost:11434/api/generate](http://localhost:11434/api/generate)",

json=\{

"model": "deepseek-v4",

"prompt": prompt,

"max\_tokens": 2,

"temperature": 0

}

)

return response.json()\["response"].strip()

* 优点：零额外显存占用
* 限制：设置 `max_tokens=2` 降低计算负担
*

### 方案B（辅助）：关键词驱动 + 轻量分类器

* 已集成的15对对立关键词作为第一道过滤
* 命中关键词后，用 **scikit-learn 逻辑回归**（模型\<1MB）做二次确认
* CPU推理仅微秒级，零GPU消耗

### 结论

* 矛盾关键词未命中 → 直接跳过
* 关键词命中 → 调用方案A进行二次确认
* 避免频繁API调用，同时保证精度

## 问题三：递归消化的终止条件

### 联合刹车机制

#### 刹车1：深度限制（硬终止）

最大递归深度 **3 层**：

* 第0层：外部原始猎物
* 第1层：内部对话猎物
* 第2层：元认知记录
* 第3层：对元认知的二次反思
  超过3层不再生成新内部猎物。

#### 刹车2：信息增益衰减（软终止）

from sklearn.metrics.pairwise import cosine\_similarity

def gain\_is\_sufficient(new\_inner\_text, parent\_inner\_text, threshold=0.9):

emb\_new = get\_embedding(new\_inner\_text)

emb\_parent = get\_embedding(parent\_inner\_text)

sim = cosine\_similarity(\[emb\_new], \[emb\_parent])\[0]\[0]

return sim \< threshold

相似度 > 0.9 → 讨论原地打转，终止。

#### 刹车3：能量预算（代谢终止）

class EnergyBudget:

def **init**(self, daily\_budget=1000):

self.remaining = daily\_budget

def consume(self, cost):

if self.remaining >= cost:

self.remaining -= cost

return True

return False

当预算耗尽，挂起递归队列，等待下一代谢周期处理。

#### 刹车4：语义闭环检测（逻辑终止）

内部猎物消化结论为“矛盾已解决”时自然停止。

### 递归调用实现

def digest\_prey(self, prey, depth=0):

if depth > 3:

return

if not self.energy\_budget.consume(COST\_PER\_DIGEST):

self.deferred\_queue.append((prey, depth))

return

# ... 消化处理 ...

if inner\_prey and gain\_is\_sufficient(inner\_prey, prey.text):

self.digest\_prey(inner\_prey, depth + 1)

## 落地方案总结

1. **惊奇处理**：实现三级级联 + 回调注册表，默认开启注意力提升和反思快照。
2. **矛盾检测**：主用 Ollama 零样本判断，辅以关键词预筛选，零额外资源。
3. **递归安全**：联合四重刹车（深度、信息增益、能量预算、语义闭环）。

这三个设计都符合曦和轻量、响应优先的哲学，无需引入重量级外部框架。

​
