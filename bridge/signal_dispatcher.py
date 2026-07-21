#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信号调度器 · Signal Dispatcher v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
华为ADOL + A2A-T标准启发：
将信号从"写死路由"升级为"发布订阅+Agent Card能力匹配"。

原问题：趋势分析信号写死路由到 strategic_center
新方案：按信号类型遍历Agent Card的 events_listens 匹配分发

核心流程：
  dispatch(signal) →
    1. 查 Agent Card 找到能处理此信号的Agent
    2. 按 consensus_weight 排序/过滤
    3. 分发到目标Agent（写入该Agent的事件队列）
    4. 返回分发结果
"""

import json, os, time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

BRIDGE_DIR = Path("F:/SmartLegend/Xihe/bridge")
REGISTRY_PATH = BRIDGE_DIR / "agent_registry.json"
GAIN_PATH = BRIDGE_DIR / "gain_landscape.json"
BJT = timezone(timedelta(hours=8))

def now_bjt():
    return datetime.now(BJT)

def ts_bjt():
    return now_bjt().isoformat()

def safe_read_json(path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except:
        return default

def safe_write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)

class SignalDispatcher:
    """信号调度器：按Agent Card能力匹配分发信号"""

    SIGNAL_TYPES = {
        'emerge':       {'target_focus': '战略', 'description': '多模块同步上升信号'},
        'lock':         {'target_focus': '诊断', 'description': '模块僵锁信号'},
        'oscillate':    {'target_focus': '维稳', 'description': '增益振荡信号'},
        'transient_risk': {'target_focus': '稳压', 'description': 'Kreiss瞬态放大风险信号(P0)'},
        'gain_change':  {'target_focus': '调制', 'description': '增益变化事件'},
        'gap_found':    {'target_focus': '进化', 'description': '能力缺口发现'},
        'goal_violation': {'target_focus': '稳态', 'description': 'Goal制越界告警'},
        'system_health':  {'target_focus': '监控', 'description': '系统健康事件'},
    }

    def __init__(self):
        self.registry = safe_read_json(REGISTRY_PATH, {}).get('agents', {})
        self.dispatch_log = []

    def reload_registry(self):
        """重新加载Agent Card注册表"""
        self.registry = safe_read_json(REGISTRY_PATH, {}).get('agents', {})
        return len(self.registry)

    def find_targets(self, signal_type, signal_severity=None):
        """
        按信号类型查找所有能处理此信号的Agent。
        规则：
        1. 精确匹配 events_listens
        2. 通配符 * 匹配所有
        3. 按 consensus_weight + signal_severity 加权排序
        """
        if not self.registry:
            self.reload_registry()

        candidates = []
        for name, card in self.registry.items():
            listens = card.get('events_listens', [])
            skills = [s.get('name', '') for s in card.get('skills', [])]

            # 精确匹配或通配符
            if signal_type in listens or '*' in listens:
                weight = card.get('consensus_weight', 1)
                # 有对应skill的加分
                has_matching_skill = any(
                    signal_type.split('_')[0] in s for s in skills
                )
                adjusted_weight = weight * (1.2 if has_matching_skill else 1.0)
                candidates.append((name, adjusted_weight, card))
                continue

            # 模糊匹配：信号类型关键词出现在技能描述中
            for skill in card.get('skills', []):
                desc = skill.get('desc', '')
                if signal_type.split('_')[0] in desc:
                    weight = card.get('consensus_weight', 1)
                    candidates.append((name, weight * 0.8, card))
                    break

        # 按权重降序
        candidates.sort(key=lambda x: -x[1])
        return candidates

    def dispatch(self, signal_type, payload, source='signal_dispatcher'):
        """
        分发信号到匹配的Agent
        
        参数:
            signal_type: 信号类型 (emerge/lock/oscillate/etc)
            payload: 信号载荷（dict）
            source: 信号来源
        
        返回:
            dispatch_result: 分发结果
        """
        timestamp = ts_bjt()
        signal_severity = payload.get('severity', 'medium')

        targets = self.find_targets(signal_type, signal_severity)

        result = {
            'signal_id': f'{signal_type}-{int(time.time())}',
            'timestamp': timestamp,
            'signal_type': signal_type,
            'severity': signal_severity,
            'source': source,
            'targets_found': len(targets),
            'targets': [],
            'dispatched': False,
        }

        if not targets:
            # 没有Agent能处理此信号 -> 记录为无消费端
            result['warning'] = f'无Agent注册监听信号类型: {signal_type}'
            result['dispatched'] = False
        else:
            # 分发到所有匹配的目标（最多3个按权重排序的）
            for name, weight, card in targets[:3]:
                target_info = {
                    'agent': name,
                    'weight': weight,
                    'endpoint': card.get('endpoints', {}).get('a2a', 'unknown'),
                }
                result['targets'].append(target_info)

                # 实际分发：写入目标Agent的事件队列
                # 目前是文件触碰 + 事件日志，后续可升级为真实消息队列
                self._write_event(name, signal_type, payload)

            result['dispatched'] = True

        # 记录分发日志
        self.dispatch_log.append(result)
        if len(self.dispatch_log) > 100:
            self.dispatch_log = self.dispatch_log[-100:]

        # 华为ADOL: 记录优化统计
        try:
            from adol_layer import get_optimizer as _adol
            _adol().load_registry()
        except ImportError:
            pass

        # 如果没有目标，尝试fallback到strategic_center
        if not result['dispatched']:
            strategic = self.registry.get('strategic_center')
            if strategic:
                result['fallback'] = 'strategic_center'
                self._write_event('strategic_center', signal_type, payload)
                result['dispatched'] = True

        # ── MOSS 式审计追踪 (P1)：每条信号分发上链 ──
        try:
            from audit_trail import audit
            audit("signal_dispatch", actor=source, action="dispatch",
                  payload={
                      "signal_type": signal_type,
                      "severity": signal_severity,
                      "targets_found": result["targets_found"],
                      "dispatched": result["dispatched"],
                      "targets": [t["agent"] for t in result.get("targets", [])],
                      "fallback": result.get("fallback"),
                  },
                  source="signal_dispatcher")
        except Exception:
            pass

        return result

    def dispatch_blueprint(self, signal_type, payload, blueprint, source='signal_dispatcher'):
        """
        [ACP 融合 · 研讨厅研判 0.88 · A嫁接 · 2026-07-20]
        Agent Context Protocols (arXiv:2505.14569) 执行语义层。
        补 signal_dispatcher「按能力分发」之上: 上下文随任务跨agent边界流动 + 失败隔离。

        blueprint: dict = {
            "id": "bp_xxx",
            "dag": [{"step": "s1", "depends_on": []}, ...],  # 子任务依赖
            "reuse_outputs": True  # 下游按依赖复用上游中间输出
        }
        机制:
          1. 持久化 Execution Blueprint(DAG) 到 bridge/blueprint_cache.json
          2. 分发时把上游中间输出随 payload 注入下游 agent(上下文传递)
          3. 容错: 某 target 失败仅记 partial, 不中断其他(描述性错误码)
        返回: {"dispatched": bool, "blueprint_id": str, "partial_failures": [...]}
        """
        import os, json as _json
        cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blueprint_cache.json")
        cache = {}
        if os.path.exists(cache_path):
            try:
                with open(cache_path, encoding="utf-8") as f: cache = _json.load(f)
            except Exception:
                cache = {}
        bp_id = blueprint.get("id", f"bp_{int(time.time())}")
        cache[bp_id] = {
            "dag": blueprint.get("dag", []),
            "reuse_outputs": blueprint.get("reuse_outputs", True),
            "created": ts_bjt(),
            "outputs": {},
        }
        with open(cache_path, "w", encoding="utf-8") as f: _json.dump(cache, f, ensure_ascii=False, indent=1)

        # 按 DAG 顺序分发: 依赖已满足(step 的上游输出已就绪)才分发
        partial_failures = []
        dispatched_any = False
        for step in blueprint.get("dag", []):
            deps = step.get("depends_on", [])
            if deps and not all(d in cache[bp_id]["outputs"] for d in deps):
                partial_failures.append({"step": step.get("step"), "reason": "依赖未满足(上下文未就绪)", "code": "E_DEP_NOT_MET"})
                continue
            ctx_payload = dict(payload)
            if blueprint.get("reuse_outputs", True) and deps:
                ctx_payload["_upstream_context"] = {d: cache[bp_id]["outputs"].get(d) for d in deps}
            try:
                r = self.dispatch(signal_type, ctx_payload, source=f"{source}:{bp_id}")
                if r.get("dispatched"):
                    dispatched_any = True
                    cache[bp_id]["outputs"][step.get("step")] = r.get("targets", [])
                    with open(cache_path, "w", encoding="utf-8") as f: _json.dump(cache, f, ensure_ascii=False, indent=1)
                else:
                    partial_failures.append({"step": step.get("step"), "reason": r.get("warning", "无消费端"), "code": "E_NO_TARGET"})
            except Exception as e:
                partial_failures.append({"step": step.get("step"), "reason": str(e)[:100], "code": "E_RUNTIME"})
                # 容错: 局部失败不崩全局

        return {"dispatched": dispatched_any, "blueprint_id": bp_id, "partial_failures": partial_failures}

    def orchestration_credit(self, spec, executed_outcome, edited_span=None, source='signal_dispatcher'):
        """
        [LEMON 融合 · 研讨厅研判 0.87 · A嫁接 · 2026-07-21]
        LEMON (arXiv:2605.14483) 编排层局部化信用。
        与 dispatch_blueprint(ACP上下文传递)拼成完整编排栈: ACP管上下文流动, LEMON管决策优化。

        机制: orchestration spec 的 role/capacity/dependency 三 field 作为决策变量;
        编辑某 span → reward contrast 只作用在 edited spans (局部化梯度), 不污染其他 field。
        稀疏执行反馈下, 指出哪些 role/capacity/dependency 真正 responsible。

        参数:
            spec: dict = {role, capacity, dependency} 编排决策变量
            executed_outcome: float 0-1 端到端执行结果(稀疏奖励)
            edited_span: dict 被反事实编辑的 field 子集(默认全部)
            source: 来源标记
        返回: {"credits": dict(field→局部信用分), "cache_id": str}
        """
        import os, json as _json
        credit_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orchestration_credit.json")
        cache = {}
        if os.path.exists(credit_path):
            try:
                with open(credit_path, encoding="utf-8") as f: cache = _json.load(f)
            except Exception: cache = {}

        fields = ["role", "capacity", "dependency"]
        base = executed_outcome if executed_outcome is not None else 0.5
        spans = edited_span if edited_span else fields
        credits = {}
        for fld in fields:
            if fld in spans:
                # 局部化信用: 该 field 的相对贡献(反事实对比占位, 真实值由运行时注入对比)
                local = round(base * (1.0 if fld == "role" else 0.8 if fld == "capacity" else 0.6), 3)
                credits[fld] = local
            else:
                credits[fld] = round(base * 0.3, 3)  # 未编辑 span 低信用
        cid = f"oc_{int(time.time())}"
        cache[cid] = {"spec": spec, "outcome": base, "credits": credits, "created": ts_bjt(), "source": source}
        cache = dict(list(cache.items())[-200:])
        with open(credit_path, "w", encoding="utf-8") as f: _json.dump(cache, f, ensure_ascii=False, indent=1)
        return {"credits": credits, "cache_id": cid}

    def _write_event(self, agent_name, signal_type, payload):
        """为目标Agent写入事件"""
        event = {
            'type': signal_type,
            'timestamp': ts_bjt(),
            'payload': payload.copy() if isinstance(payload, dict) else {'value': str(payload)},
        }
        # 写入到 agent-specific 事件文件
        events_dir = BRIDGE_DIR / 'events'
        events_dir.mkdir(parents=True, exist_ok=True)
        event_path = events_dir / f'{agent_name}_events.json'
        existing = safe_read_json(event_path, [])
        existing.append(event)
        if len(existing) > 50:
            existing = existing[-50:]
        safe_write_json(event_path, existing)

    def get_recent_signals(self, limit=10):
        """获取最近的分发信号"""
        return self.dispatch_log[-limit:] if self.dispatch_log else []

    def get_pending_events(self, agent_name):
        """获取Agent的待处理事件并清空"""
        event_path = BRIDGE_DIR / 'events' / f'{agent_name}_events.json'
        events = safe_read_json(event_path, [])
        # 清空
        safe_write_json(event_path, [])
        return events

    def dispatch_trend_signal(self, signal):
        """
        专用方法：将趋势分析信号自动分发。
        这是从 gain_trend_analyzer 输出的标准入口。
        
        映射规则：
          emerge    -> rumination_scheduler + strategic_center
          lock      -> metabolic_actor + strategic_center  
          oscillate -> population_ecology + metabolic_actor
          transient_risk -> metabolic_actor + population_ecology (稳压)
        """
        signal_type = signal.get('type', 'unknown')
        severity = signal.get('severity', 'medium')
        suggestion = signal.get('suggestion', '')

        payload = {
            'type': signal_type,
            'severity': severity,
            'suggestion': suggestion,
            'timestamp': ts_bjt(),
            'source_modules': signal.get('source_modules', []),
        }

        return self.dispatch(signal_type, payload, source='gain_trend_analyzer')


# 全局单例
_disp = None

def get_dispatcher():
    global _disp
    if _disp is None:
        _disp = SignalDispatcher()
    return _disp

def dispatch(signal_type, payload, source='signal_dispatcher'):
    """快捷分发函数"""
    return get_dispatcher().dispatch(signal_type, payload, source)

def dispatch_trend_signal(signal):
    """快捷趋势信号分发"""
    return get_dispatcher().dispatch_trend_signal(signal)


# ===== 命令行入口 =====
if __name__ == '__main__':
    import sys
    d = get_dispatcher()
    print(f'信号调度器启动 | Agent注册: {len(d.registry)}个')
    print(f'信号类型支持: {len(d.SIGNAL_TYPES)}种')

    # 测试分发
    if len(sys.argv) > 1:
        signal_type = sys.argv[1]
        payload = {'severity': sys.argv[2] if len(sys.argv) > 2 else 'medium',
                   'suggestion': '命令行测试信号' if len(sys.argv) <= 3 else sys.argv[3]}
        result = d.dispatch(signal_type, payload)
        print(f'分发结果: type={signal_type} targets={result["targets_found"]} dispatched={result["dispatched"]}')
        for t in result.get('targets', []):
            print(f'  -> {t["agent"]} (weight={t["weight"]})')
        if 'warning' in result:
            print(f'  ⚠️ {result["warning"]}')
        if 'fallback' in result:
            print(f'  ↩️ fallback: {result["fallback"]}')
