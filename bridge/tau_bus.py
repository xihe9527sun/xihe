"""
τ 统一总线 · 七层架构跨层通信协议
基于华为τ缩放理论设计 —— 内存级事件总线替代文件I/O

设计原则：
  ① 每层有专属τ值（目标延迟预算）
  ② 统一事件格式替代每层手写文件接口
  ③ τ在哪层产生，就在哪层解决
  ④ 跨层调用延迟 ≤ 1次心跳（0.5s）
"""

import json, time, os, threading, queue
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional, Callable

BJT = timezone(timedelta(hours=8))
XIHE = Path("F:/SmartLegend/Xihe")
CORTEX = XIHE / "cortex"

# ── τ 配置 ──
# 每层的目标延迟（秒）
TAU_TARGET = {
    "L0": 0.5,    # 物理层：端口扫描间隔
    "L1": 0.1,    # 知识层：赫布检索
    "L2": 0.5,    # 代谢层：心跳间隔
    "L3": 5.0,    # 拓扑层：社区检测（可慢些）
    "L4": 1.0,    # 催化层：酶匹配
    "L5": 2.0,    # 自反层：反思评估
    "L6": 1.0,    # 免疫层：安全检查
    "L7": 10.0,   # 涌现层：自我决定（分钟级）
}

# 事件优先级
P_HIGH = 0   # 立即处理（告警、熔断）
P_NORMAL = 1 # 正常处理
P_LOW = 2    # 可延迟（日志、统计）

# ── 事件格式 ──
@dataclass
class TauEvent:
    source: str            # 来源层，如 "L2"
    target: str            # 目标层，如 "L5"，"*" 表示广播
    event_type: str        # 事件类型，如 "sensor.scan", "knowledge.recall"
    payload: dict          # 事件数据
    priority: int = P_NORMAL
    timestamp: float = field(default_factory=time.time)
    tau_budget: float = 1.0  # 此事件的延迟预算（秒）
    id: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = f"{self.source}→{self.target}:{self.event_type}:{int(self.timestamp*1000)}"
    
    def to_dict(self):
        return {
            "id": self.id, "source": self.source, "target": self.target,
            "event_type": self.event_type, "payload": self.payload,
            "priority": self.priority, "timestamp": self.timestamp,
            "tau_budget": self.tau_budget
        }

# ── τ 总线 ──
class TauBus:
    """内存事件总线，七层之间通过它通信"""
    
    def __init__(self):
        self._queues = {f"L{i}": queue.PriorityQueue() for i in range(8)}
        self._subscribers = defaultdict(list)  # event_type → [callbacks]
        self._stats = {"total_events": 0, "tau_violations": 0, "by_source": defaultdict(int)}
        self._running = False
        self._lock = threading.Lock()
        self._tau_log = []
    
    def publish(self, event: TauEvent):
        """发布事件到目标层队列"""
        with self._lock:
            self._stats["total_events"] += 1
            self._stats["by_source"][event.source] += 1
        
        # 检查τ预算
        elapsed = time.time() - event.timestamp
        if elapsed > event.tau_budget:
            with self._lock:
                self._stats["tau_violations"] += 1
            self._tau_log.append({
                "ts": datetime.now(BJT).isoformat(),
                "event": event.id,
                "tau_budget": event.tau_budget,
                "actual": round(elapsed, 3)
            })
        
        item = (event.priority, event.timestamp, event)
        
        if event.target == "*":
            for q in self._queues.values():
                q.put(item)
        elif event.target in self._queues:
            self._queues[event.target].put(item)
        
        # 同时触发订阅者
        for pattern, cbs in self._subscribers.items():
            if event.event_type.startswith(pattern.replace("*", "")):
                for cb in cbs:
                    try: cb(event)
                    except: pass
    
    def subscribe(self, event_type_pattern: str, callback: Callable):
        """订阅事件类型（支持通配符）"""
        self._subscribers[event_type_pattern].append(callback)
    
    def consume(self, layer: str, timeout: float = 0.1) -> Optional[TauEvent]:
        """从指定层队列消费一个事件"""
        q = self._queues.get(layer)
        if not q: return None
        try:
            _, _, event = q.get(timeout=timeout)
            return event
        except queue.Empty:
            return None
    
    def get_stats(self) -> dict:
        with self._lock:
            return {
                "total_events": self._stats["total_events"],
                "tau_violations": self._stats["tau_violations"],
                "tau_compliance": round(
                    (1 - self._stats["tau_violations"] / max(self._stats["total_events"], 1)) * 100, 1
                ),
                "by_source": dict(self._stats["by_source"]),
                "recent_violations": self._tau_log[-5:]
            }

# ── 全局单例 ──
BUS = TauBus()

# ── 事件类型注册表 ──
EVENT_TYPES = {
    # L0 → *
    "sensor.scan": {"desc": "端口扫描完成", "source": "L0", "tau": 0.5},
    "sensor.alert": {"desc": "端口异常", "source": "L0", "tau": 0.1},
    # L1 → L2
    "knowledge.edge_updated": {"desc": "赫布边更新", "source": "L1", "tau": 0.1},
    "knowledge.recall": {"desc": "知识检索请求", "source": "L1", "tau": 0.1},
    # L2 → L3, L4
    "route.path_selected": {"desc": "路径被选中", "source": "L2", "tau": 0.5},
    "route.path_dropped": {"desc": "路径被淘汰", "source": "L2", "tau": 0.5},
    # L3 → L4
    "topology.module_found": {"desc": "新模块发现", "source": "L3", "tau": 5.0},
    # L4 → L5
    "catalysis.enzyme_activated": {"desc": "酶激活", "source": "L4", "tau": 1.0},
    "catalysis.new_edge": {"desc": "新催化边", "source": "L4", "tau": 1.0},
    # L5 → L6, L7
    "meta.anomaly_detected": {"desc": "异常检测", "source": "L5", "tau": 2.0},
    "meta.decision_needed": {"desc": "需要决策", "source": "L5", "tau": 2.0},
    # L6 → L0
    "immunity.alert": {"desc": "安全告警", "source": "L6", "tau": 0.5},
    # L7 → *
    "will.daily_plan": {"desc": "今日计划", "source": "L7", "tau": 10.0},
}

# ── τ 合规检查器（可集成到watchman） ──
def tau_compliance_check() -> dict:
    """检查各层τ合规情况"""
    stats = BUS.get_stats()
    report = {
        "timestamp": datetime.now(BJT).isoformat(),
        "tau_compliance": stats["tau_compliance"],
        "total_events": stats["total_events"],
        "violations": stats["tau_violations"],
        "layer_stats": {}
    }
    
    # 每层统计
    for layer, target_tau in TAU_TARGET.items():
        events = stats["by_source"].get(layer, 0)
        report["layer_stats"][layer] = {
            "events": events,
            "tau_target": target_tau,
            "tau_unit": "s"
        }
    
    return report

# ── 便捷发布函数 ──
def emit(event_type: str, source: str, target: str = "*", payload: dict = None, priority: int = P_NORMAL):
    """快速发布一个τ事件"""
    et = EVENT_TYPES.get(event_type, {})
    tau = et.get("tau", 1.0)
    event = TauEvent(
        source=source,
        target=target,
        event_type=event_type,
        payload=payload or {},
        priority=priority,
        tau_budget=tau
    )
    BUS.publish(event)
    return event

if __name__ == "__main__":
    print("\n🧬 τ 统一总线 · 测试")
    print("=" * 40)
    
    # 注册订阅者
    def on_scan(e):
        print(f"  [订阅者] 收到: {e.event_type} 来自 {e.source} 负载: {e.payload}")
    
    BUS.subscribe("sensor.*", on_scan)
    
    # 发布事件
    emit("sensor.scan", "L0", "L1", {"port": 4326, "status": "up"})
    emit("sensor.alert", "L0", "L6", {"port": 4321, "status": "down"})
    emit("knowledge.edge_updated", "L1", "L2", {"edge": "E1→E2", "weight": 0.85})
    emit("route.path_selected", "L2", "L4", {"path": "digest→insight", "hits": 42})
    
    # 消费事件
    print("\n  各层消费:")
    for layer in ["L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"]:
        e = BUS.consume(layer, timeout=0.1)
        if e:
            print(f"  {layer} ← {e.source}:{e.event_type} [{e.tau_budget}s]")
    
    # τ合规报告
    print("\n📊 τ合规报告:")
    report = tau_compliance_check()
    print(f"  合规率: {report['tau_compliance']}%")
    print(f"  总事件: {report['total_events']}")
    print(f"  τ违规: {report['violations']}")
    
    # 写入cortex供面板读取
    (CORTEX / "tau-bus-stats.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("\n✅ τ总线测试完成")
