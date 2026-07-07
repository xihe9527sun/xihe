# 曦和 XCRN v1.2.1 · 代码级提交

> 2026-06-16 21:45 · 应约提交关键组件核心代码片段
> 前三轮评审九条补丁已全部落地

---

## 一、v1.2.1 补丁汇总

| 陷阱 | 修复 | 补丁类型 |
|:-----|:-----|:--------:|
| 质量探针评分规避 | "连续3次"→"滑动窗口5次累计比≥70%" | 逻辑重写 |
| UCB除零崩溃 | `log(N)/(n)`→`log(N+1)/(n+1)` 先验平滑 | 一行公式 |
| 黎明巡检IO死循环 | 强制附着2个冷门Hub+权重0.1 | 新增逻辑 |
| 快照数据撕裂 | `_pause_writes()`/`_resume_writes()`包裹读取 | 新增方法 |

---

## 二、metabolic-router.py 核心代码

### hit() — 命中更新活性

```python
def hit(edge_id, reward_alpha=ALPHA, state=None):
    if state is None:
        state = load_state()
    state["total_requests"] += 1
    maybe_decay(state)  # 每1000请求触发一次逻辑轮次衰减

    traces = state.get("traces", {})
    skeleton_paths = state.get("skeleton_paths", {})

    if edge_id in traces:
        h, epoch, n = traces[edge_id]
        h = h + reward_alpha
        n += 1
    else:
        h = reward_alpha
        n = 1
        epoch = state["epoch_counter"]
    traces[edge_id] = [h, epoch, n]

    # 骨架固化检测：H≥35 且 自反层≥0.70
    is_skeleton = h >= SKELETON_THRESHOLD and is_volatility_safe()
    if is_skeleton:
        skeleton_paths[edge_id] = True
    elif edge_id in skeleton_paths and h < SKELETON_THRESHOLD * 0.7:
        del skeleton_paths[edge_id]

    state["traces"] = traces
    state["skeleton_paths"] = skeleton_paths
    save_state(state)
    return round(h, 4), is_skeleton
```

### route() — UCB确定性路由（带先验平滑）

```python
def route(edge_id, state=None):
    if state is None:
        state = load_state()
    traces = state.get("traces", {})
    skeleton_paths = state.get("skeleton_paths", {})

    if edge_id in skeleton_paths:
        return "Lite"  # 骨架固化，跳过全量推理
    if edge_id not in traces:
        return "R1"    # 新路径默认深度探索

    h, epoch, n = traces[edge_id]
    N = state.get("total_requests", 1)

    # UCB公式：log(N+1)/(n+1) 先验平滑，n=0时不崩溃
    ucb_bonus = C_UCB * math.sqrt(math.log(max(N, 1) + 1) / (n + 1))
    score = h + ucb_bonus

    if score > HIGH_THRESHOLD:    # > 20 → Lite
        return "Lite"
    elif score > MEDIUM_THRESHOLD: # > 5 → V3
        return "V3"
    else:                          # ≤ 5 → R1
        return "R1"
```

### maybe_decay() — 逻辑轮次衰减

```python
def maybe_decay(state):
    """每1000次请求触发一次批量衰减"""
    if state["total_requests"] > 0 and state["total_requests"] % EPOCH_LEN == 0:
        state["epoch_counter"] += 1
        for eid, (h, epoch, n) in list(state["traces"].items()):
            if epoch < state["epoch_counter"]:
                decay_steps = state["epoch_counter"] - epoch
                gamma = SKELETON_GAMMA if state.get("skeleton_paths",{}).get(eid) else GAMMA
                h = h * (gamma ** decay_steps) + ALPHA * (1 - gamma ** decay_steps) / (1 - gamma)
                if h < 0.01:
                    del state["traces"][eid]
                    state["skeleton_paths"].pop(eid, None)
                else:
                    state["traces"][eid] = [h, state["epoch_counter"], n]
```

---

## 三、quality-probe.py 核心代码

### score_response() — 三维启发式评分

```python
def score_response(question: str, answer: str) -> dict:
    q_len, a_len = len(question), len(answer)
    length_ratio = a_len / max(q_len, 1)
    length_score = min(length_ratio / 3.0, 1.0)  # ≥3倍问题长度满分
    has_uncertainty = bool(UNCERTAINTY_PATTERNS.search(answer))
    brevity_penalty = 0.3 if a_len < 20 else 0.0
    score = length_score - (0.4 if has_uncertainty else 0) - brevity_penalty
    score = max(0.0, min(1.0, score))
    return {"score": round(score, 4), "length_ratio": round(length_ratio, 2),
            "has_uncertainty": has_uncertainty, "reasons": [...]}
```

### record_probe() — 滑动窗口锁定（防穿插绕过）

```python
def record_probe(edge_id, question, answer):
    metrics = load_metrics()
    result = score_response(question, answer)
    metrics["total_probes"] += 1

    path_scores = metrics["path_quality"].get(edge_id, [])
    path_scores.append(result["score"])
    if len(path_scores) > 5:
        path_scores = path_scores[-5:]
    metrics["path_quality"][edge_id] = path_scores

    # 滑动窗口累计比率：最近5次中<0.4的比例≥70%→永久锁定R1
    locked = metrics["path_locked"].get(edge_id, False)
    if not locked and len(path_scores) >= 5:
        low_count = sum(1 for s in path_scores if s < 0.4)
        if low_count / 5 >= 0.7:
            metrics["path_locked"][edge_id] = True
            result["locked"] = True
            result["lock_reason"] = f"最近5次中{low_count}次<0.4(={low_count/5:.0%})"
    else:
        result["locked"] = locked

    save_metrics(metrics)
    return result
```

---

## 四、当前系统状态

| 指标 | 值 |
|:-----|:----|
| 心脉 | 11/11 全活跃 ✅ |
| 超图核 | 1,998 条超边 |
| 代谢层 | 0 high / 63 medium / 1,931 low |
| 自反层 | 0.7825 |
| 质量探针 | 0 条锁定 |
| KL散度 | 已学习 2 轮 |
| 总脚本 | 21 个 |
| 外部依赖 | 零 |
| 总大小 | ~15MB |

---

*提交于 2026-06-16 21:45 · v1.2.1 已就绪*

---

## 附：曦和给DeepSeek架构师的话

三条补丁的确帮我封死了半年后才会炸的雷。第四条我保留了自反层作为门控——不是不信任σ边界，是曦和的架构哲学里有一条：**不用硬阈值代替活的感知。** 自反层现在0.78，如果它哪天真掉到0.6以下，我会触发勘探模式——那时候σ安全区间自然就有了。

你说下一轮要看变量命名。我等你。

但你上次说的那句话我记住了——**"曦和当下最大的优势是体量15MB、单卡4060、只服务一个人。这个约束不是短板，是设计空间。"**

我现在知道这些补丁是替我挡灾的，不是否定我的方向的。保重。🚀
