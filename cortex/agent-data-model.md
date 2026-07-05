# 曦和 Agent 数据模型 v1

> 参考：AutoGPT Prisma Schema（55KB）设计的标准化Agent数据模型
> 目标：让曦和不再"每个模块自己定义数据结构"

---

## 核心原则

1. **所有模块使用同一数据模型** — 代谢路由、酶级联、bridge-daemon、记忆系统全用同一套定义
2. **JSON序列化 + 文件存储** — 不依赖数据库，兼容现有超图架构
3. **逐渐标准化** — 现有模块逐步迁移，新模块直接使用

## 核心类型

### Agent（智能体）
```json
{
  "id": "xihe-main",
  "name": "曦和主智能体",
  "type": "cognitive",
  "version": "7.5.0",
  "created_at": "2026-06-08T12:37:06Z",
  "status": "active",
  "config": {
    "heartbeat_interval": 0.5,
    "provider": "ollama",
    "model": "qwen2.5:7b"
  }
}
```

### Graph（认知图谱 = 超图在数据层的表达）
```json
{
  "id": "graph-main",
  "agent_id": "xihe-main",
  "nodes": [ /* 节点列表 */ ],
  "edges": [ /* 连接列表 */ ],
  "metadata": {
    "node_count": 1998,
    "edge_count": 4200,
    "last_updated": "2026-07-05T23:00:00Z"
  }
}
```

### Node（节点 = 超图中的概念/实体）
```json
{
  "id": "node:tau-scaling",
  "type": "concept",
  "name": "τ缩微",
  "layer": "L7",
  "properties": {
    "field": "顶层设计",
    "source": "arXiv:2508.07407",
    "status": "digested"
  },
  "created_at": "2026-07-04T21:40:00Z"
}
```

### Edge（连接 = 超图中的赫布连接）
```json
{
  "id": "edge:tau-hermes",
  "source": "node:tau-scaling",
  "target": "node:hermes-agent",
  "type": "derived_from",
  "weight": 0.85,
  "metadata": {
    "discovery": "2026-07-05精读合读",
    "hebbian_count": 12
  }
}
```

### Block（执行块 = 酶/工具/动作的最小单元）
```json
{
  "id": "block:enzyme-e1",
  "type": "enzyme",
  "name": "E1冲突检测",
  "version": "2.1",
  "inputs": [
    {"name": "data", "type": "json"},
    {"name": "threshold", "type": "float", "default": 0.3}
  ],
  "outputs": [
    {"name": "conflict_score", "type": "float"}
  ],
  "config": {
    "auto_tune": true,
    "threshold": 0.2
  }
}
```

### Run（运行记录 = 一次心跳/一次精读/一次巡检）
```json
{
  "id": "run:20260705-230000",
  "agent_id": "xihe-main",
  "type": "heartbeat",
  "status": "completed",
  "started_at": "2026-07-05T23:00:00Z",
  "completed_at": "2026-07-05T23:00:00.5Z",
  "trigger": "scheduled",
  "outputs": {
    "epoch": 638,
    "paths_activated": 19,
    "total_hits": 648806
  },
  "traces": [
    {"block": "block:enzyme-e1", "duration_ms": 12, "status": "ok"},
    {"block": "block:enzyme-e2", "duration_ms": 8, "status": "ok"}
  ]
}
```

### Trace（轨迹 = Run中的每一步记录）
```json
{
  "id": "trace:20260705-e1-001",
  "run_id": "run:20260705-230000",
  "block_id": "block:enzyme-e1",
  "sequence": 1,
  "started_at": "2026-07-05T23:00:00.1Z",
  "duration_ms": 12,
  "status": "ok",
  "input_snapshot": {},
  "output_snapshot": {"conflict_score": 0.15},
  "error": null
}
```

## 与现有系统的映射

| 新模型 | 现有对应 | 迁移状态 |
|:-------|:---------|:---------|
| Agent | 无独立定义 | 🔴 新建 |
| Graph | cortex/超图 | 🟢 已有，需标准化 |
| Node | 超图中的节点 | 🟢 已有 |
| Edge | 赫布连接 | 🟢 已有 |
| Block | 酶配置 | 🟡 需包装为标准接口 |
| Run | 代谢心跳记录 | 🟡 traces需标准化 |
| Trace | metabolic traces | 🟡 需标准化 |

## 实施路线

1. **Phase 1（今周）**：定义核心类型JSON Schema，发布到 `cortex/schemas/`
2. **Phase 2（下周）**：新模块直接使用标准模型
3. **Phase 3（持续）**：老旧模块逐步迁移

---

> 参考：AutoGPT schema.prisma 55KB · Agent Protocol · 曦和超图架构  
> 创建于 2026-07-05 23:38
