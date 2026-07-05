#!/usr/bin/env python3
"""
代谢路由器 · Metabolic Actor v2 — 专家蓝图融合版
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
基于专家蓝图§2-§4的改进:
  ① τ=0.5s: 从2秒加速到0.5秒, 对齐β/γ频段
  ② 直接权重访问: 每120跳直接读写 self-reflection-strength.json
  ③ 滑窗LTP/LTD: 用 heat_weight_bridge.v2 替代旧的anabolic_pathway
  ④ 具身认知: 系统每2分钟写"思考笔记"到F盘

依赖: 纯 Python stdlib
位置: F:/SmartLegend/Xihe/bridge/metabolic_actor.py
"""

import os
import json
import time
import sys
import random
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ── 路径 ──
XIHE_ROOT = Path("F:/SmartLegend/Xihe")
CORTEX_DIR = XIHE_ROOT / "cortex"
BRIDGE_DIR = XIHE_ROOT / "bridge"
EVENTS_DIR = BRIDGE_DIR / "events"

METABOLIC_STATE_PATH = CORTEX_DIR / "metabolic-router-state.json"
EVENTS_DIR.mkdir(parents=True, exist_ok=True)

BJT = timezone(timedelta(hours=8))

# ── τ规律参数（支持环境变量覆盖） ──
HEARTBEAT_INTERVAL = float(os.environ.get("XIHE_HEARTBEAT", "0.5"))
TOP_HITS_PER_BEAT = int(os.environ.get("XIHE_TOP_HITS", "2"))
RANDOM_EXPLORE_RATE = float(os.environ.get("XIHE_EXPLORE_RATE", "0.2"))
DECAY_CHECK_INTERVAL = int(os.environ.get("XIHE_DECAY_INTERVAL", "60"))
HIT_BOOST = float(os.environ.get("XIHE_HIT_BOOST", "0.2"))
EXPLORE_BOOST = float(os.environ.get("XIHE_EXPLORE_BOOST", "0.1"))

# ── 🌿 三才超参数（2026-06-23 盘古授 · 自然智能体框架）──
# 映射自 EcoConfig，不依赖 PyTorch
FIRE_RESET_INTERVAL = 500        # 【再生商数】每500跳触发一次定向剪枝（原fire_reset_interval）
SYMBIOSIS_BETA = 0.3             # 【共生系数】黑板消息对路径权重的调节幅度（原symbiosis_beta）
ALPHA_VITALITY = 0.5             # 调和项：活力度权重（原alpha_活力）
GAMMA_RESET = 0.1                # 调和项：重置成本权重（原gamma_重置）

# 🆕 保育期参数(对齐 mutation_pool.py v2)
NURSERY_FORCED_HIT_H = 0.3     # 保育期路径强制命中获得的H值(和HIT_BOOST接近, 防暴涨)
NURSERY_BEATS = 10              # 保育期心跳次数(到期毕业)

DECAY_FACTOR = 0.98             # γ衰退因子
EPOCH_LENGTH = 1000             # 每1000次请求触发纪元检查

# ── 使用事件总线(惊奇度过滤) ──
sys.path.insert(0, str(BRIDGE_DIR))
sys.path.insert(0, str(BRIDGE_DIR / "archive"))  # anabolic_pathway 在archive/中
import event_bus

# 🆕 Beta-Bernoulli Thompson Sampling 路由（2026-07-03 宝藏#38 N80融合）
from beta_ts_router import BetaBernoulliRouter

# ── 工具 ──

def now_bjt(): return datetime.now(BJT)
def ts_bjt(): return now_bjt().isoformat()

def safe_read_json(path, default=None):
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding="utf-8-sig"))
    except: return default

def safe_write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8-sig")
    tmp.replace(path)

# 使用事件总线(惊奇度过滤)
import event_bus as _event_bus

def emit_event(event_type, detail):
    """委托给事件总线(惊奇度过滤: 心跳不写文件, 只记计数器)"""
    _event_bus.emit(event_type, detail, source="metabolic_actor")


# ═══════════════════════════════════════════
#  Metabolic Actor — 独立心跳
# ═══════════════════════════════════════════

class MetabolicActor:
    """
    代谢路由器演员 — 独立心跳版
    
    每次心跳:
      1. 读自身状态
      2. 命中前3热点路径(维持)
      3. 随机探索1条冷路径(变异)
      4. 每30次心跳检查γ衰退
      5. 写回状态
      6. 发出事件
    """

    def __init__(self):
        self.beat_count = 0
        self.start_time = time.time()
        self.last_decay_check = time.time()
        # 🆕 预测误差引擎
        self.surprise_predictor = None
        self.credit_system = None
        # 🆕 🆕 Beta-Bernoulli Thompson Sampling 路由 (2026-07-03)
        self.beta_ts_router = BetaBernoulliRouter(warmup=20)
        self._ts_h_registered = False  # 首次beat时批量注册

    def _ensure_surprise_engine(self):
        """延迟加载预测误差引擎"""
        if self.surprise_predictor is None:
            from anabolic_pathway import SurprisePredictor, SurpriseCreditSystem
            self.surprise_predictor = SurprisePredictor()
            self.credit_system = SurpriseCreditSystem()

    def beat(self):
        """一次心跳"""
        self.beat_count += 1
        self._ensure_surprise_engine()
        
        # 1. 读自身状态
        state = safe_read_json(METABOLIC_STATE_PATH, {
            "version": 3,
            "traces": {},
            "epoch_counter": 0,
            "total_requests": 0,
            "skeleton_paths": {},
            "graveyard": {},
            "updated_at": time.time(),
        })
        
        traces = state.get("traces", {})
        if not traces:
            traces = self._init_seed_traces()
            state["traces"] = traces

        epoch = state.get("epoch_counter", 0)
        total_req = state.get("total_requests", 0)

        # 2. 按H值排序
        sorted_traces = sorted(
            traces.items(),
            key=lambda x: x[1][0] if isinstance(x[1], (list, tuple)) else 0,
            reverse=True
        )

        # 3. 命中前N条热点
        hits_applied = 0
        hot_taken = []
        hot_taken_full = []  # 🆕 v2: 完整ID（用于TS竞争感知更新）
        for eid, t in sorted_traces[:TOP_HITS_PER_BEAT]:
            h, ep, n = t
            traces[eid] = [h + HIT_BOOST, ep, n + 1]
            hot_taken.append(eid[:25])
            hot_taken_full.append(eid)  # 🆕 v2: 记录完整ID
            total_req += 1
            hits_applied += 1

        # 🆕 记录命中轨迹(供预测误差信用系统使用)
        for eid, t in sorted_traces[:TOP_HITS_PER_BEAT]:
            if self.credit_system:
                self.credit_system.record_hit(eid)

        # 🆕 处理保育期变异路径(强制命中 + 不减衰退 + 到期毕业)
        nursery_hits = 0
        for eid in list(traces.keys()):
            if ":nursery:" in eid:
                h, ep, n = traces[eid]
                # 检查保育期是否结束(访问超过10次 → 毕业)
                if n >= NURSERY_BEATS:
                    # 🆕 毕业后: 移除nursery前缀 + H值重置到正常冷启动范围
                    new_eid = "survivor:" + eid.split(":")[-1]
                    traces[new_eid] = [1.0 + h * 0.01, ep, 0]  # 重置H为正常值
                    del traces[eid]
                    emit_event("nursery.graduate", f"{eid[:30]}→{new_eid[:30]}")
                    continue
                # 强制命中(保育期保护)
                traces[eid] = [h + NURSERY_FORCED_HIT_H, ep, n + 1]
                total_req += 1
                hits_applied += 1
                nursery_hits += 1
                # 记录保育期的命中轨迹
                if self.credit_system:
                    self.credit_system.record_hit(eid)

        # 4. 随机探索一条冷路径(按照 RANDOM_EXPLORE_RATE 概率)
        explored = None
        if random.random() < RANDOM_EXPLORE_RATE and len(sorted_traces) > TOP_HITS_PER_BEAT:
            # 从后50%中随机选一条
            cold_candidates = sorted_traces[len(sorted_traces)//2:]
            if cold_candidates:
                eid, t = random.choice(cold_candidates)
                h, ep, n = t
                traces[eid] = [h + EXPLORE_BOOST, ep, n + 1]
                explored = eid[:30]
                total_req += 1
                hits_applied += 1

        # 5. 三级痕迹生命周期: 活跃 → 休眠 → 墓地(每60秒)
        now = time.time()
        if now - self.last_decay_check >= DECAY_CHECK_INTERVAL:
            self.last_decay_check = now
            decay_count = 0
            dormant_count = 0
            graveyard = state.get("graveyard", {})
            dormant = state.get("dormant", {})  # 🆕 休眠层

            for eid in list(traces.keys()):
                h, ep, n = traces[eid]

                # 跳过保育期路径(它们不受生命周期管理)
                if ":nursery:" in eid:
                    continue

                if h < 0.3 and n < 2:
                    # 极冷+极少访问 → 移入墓地(永久删除)
                    graveyard[eid] = {
                        "buried_at": time.time(),
                        "peak_h": h,
                        "total_visits": n,
                    }
                    del traces[eid]
                    decay_count += 1

                elif h < 1.0:
                    # 🆕 冷但不够死 → 移入休眠层(冻结，不移除数据)
                    dormant[eid] = {
                        "frozen_at": time.time(),
                        "h_at_freeze": h,
                        "total_visits": n,
                        "epoch_at_freeze": ep,
                    }
                    del traces[eid]
                    dormant_count += 1

                elif h < 2.0:
                    # 温路径 → 轻微衰退
                    traces[eid] = [h * DECAY_FACTOR, ep, n]

            # 🆕 休眠复活检查：休眠超过N次心跳的路径如果热度排名上升 → 复活
            if dormant:
                revived_count = 0
                for eid in list(dormant.keys()):
                    frozen_since = dormant[eid]["frozen_at"]
                    hours_frozen = (time.time() - frozen_since) / 3600
                    # 如果冻结超过6小时 → 打复活标记(让新变异补充)
                    if hours_frozen > 6:
                        # 不删除休眠记录，只是标记为可清理
                        dormant[eid]["ready_for_prune"] = True

                    # 如果某条休眠路径被外部事件"唤醒"→ 复活
                    # (目前靠新变异补充，未来可以加主动唤醒逻辑)

                # 清理超过24小时的休眠路径(彻底遗忘)
                old_dormant = {eid: info for eid, info in dormant.items()
                               if (time.time() - info.get("frozen_at", 0)) / 3600 < 24}
                pruned = len(dormant) - len(old_dormant)
                dormant = old_dormant

            state["graveyard"] = graveyard
            state["dormant"] = dormant

            if decay_count > 0 or dormant_count > 0:
                emit_event("tier.lifecycle",
                           f"墓地+{decay_count} 休眠+{dormant_count} 活跃:{len(traces)}")

            # 检查纪元推进(每1000次请求)
            if total_req // EPOCH_LENGTH > epoch:
                state["epoch_counter"] = epoch + 1
                emit_event("epoch.advance", 
                           f"纪元{epoch}→{epoch+1}, 总请求{total_req}")

            emit_event("metabolic.decay", f"γ衰退: {decay_count}条入墓地")

            # ── 🆕 预测误差驱动: 每60秒检查自反层强度变化 ──
            try:
                ref = safe_read_json(CORTEX_DIR / "reflection-strength.json", {})
                current_strength = ref.get("reflection_strength", 0.7825)
                if self.surprise_predictor:
                    pred_result = self.surprise_predictor.update(current_strength)
                    if pred_result["is_surprising"]:
                        print(f"[⚡] 惊奇! 强度{pred_result['actual']:.4f} 预测{pred_result['predicted']:.4f} "
                              f"偏差{pred_result['surprise']:.2f}σ")
            except Exception:
                pass

            # ── 🆕 滑窗LTP/LTD: 热度→强度转化(每60秒) ──
            try:
                from heat_weight_bridge import apply_ltp_ltd
                hw_result = apply_ltp_ltd()
                if hw_result["status"] == "completed":
                    emit_event("ltp_ltd.conversion",
                               f"LTP:{hw_result['ltp']} LTD:{hw_result['ltd']} "
                               f"维度:{hw_result['dimensions']}")
            except Exception as e:
                pass

        # 🆕 TS路由: 将从H值路由注册到TS路由器(首次执行时)
        if not self._ts_h_registered and traces:
            reg = self.beta_ts_router.register_from_h_values(traces)
            if reg > 0:
                self._ts_h_registered = True

        # 🆕 TS路由 v2: 竞争感知更新 (每次beat后执行)
        if self._ts_h_registered and hot_taken_full:
            try:
                all_path_ids = list(traces.keys())
                # 被H值路由选中的路径 → success, 未选中 → 隐式失败
                self.beta_ts_router.batch_update_with_competition(
                    hot_taken_full, all_path_ids, success_rate=0.7)
            except Exception as e:
                pass  # TS路由失败不应影响主路由流程

        # 6. 写回状态
        state["traces"] = traces
        state["total_requests"] = total_req
        state["updated_at"] = now
        safe_write_json(METABOLIC_STATE_PATH, state)

        # 7. 发出事件
        if hits_applied > 0:
            emit_event("metabolic.hit", 
                       f"命中{hot_taken[:2]}" + (f" 探索:{explored}" if explored else ""))

        # 8. 生成摘要(供其他Actor读)
        summary = {
            "beat": self.beat_count,
            "hits": hits_applied,
            "explored": explored is not None,
            "hot": hot_taken[:2],
            "epoch": state["epoch_counter"],
            "total_req": total_req,
            "traces_count": len(traces),
        }
        return summary


    def _init_seed_traces(self):
        """首次启动时从edges.json读取种子"""
        import os
        edges_path = CORTEX_DIR / "edges.json"
        if not edges_path.exists():
            return {}
        try:
            data = json.loads(edges_path.read_text(encoding="utf-8-sig"))
            edges = data if isinstance(data, list) else data.get("edges", [])
            traces = {}
            for i, edge in enumerate(edges[:200]):
                src = edge.get("source", f"node:{i}")
                traces[f"node:{src}"] = [3.0 + random.random() * 5, 0, 0]
            return traces
        except:
            return {}


# ── 守护循环 ──

def daemon_loop():
    actor = MetabolicActor()
    print(f"[metabolic-actor] 心跳启动 τ=2s  {ts_bjt()}")
    
    # ── 🆕 具身认知: 系统用手写笔记 ──
    _last_note_beat = 0
    # ── 🆕 直接权重访问: 每120跳(~1min)直接调试自反层 ──
    _last_weight_beat = 0
    # ── 🆕 好奇心狩猎: 跟踪上次狩猎时间 ──
    _last_hunt_check = 0
    # ── 🆕 内在猎物生成: 跟踪上次生成时间 ──
    _last_internal_prey = 0
    # ── 🆕 猎物消化: 跟踪上次消化时间 ──
    _last_digest_check = 0
    # ── 🆕 级联调度: 跟踪上次触发时间 ──
    _last_cascade_beat = 0
    # ── 🆕 种群生态: 跟踪上次计算时间 ──
    _last_population_beat = 0
    # ── 🆕 🆕 觅食循环: 跟踪上次觅食检查 ──
    _last_forage_beat = 0
    # ── 🆕 🆕 催化循环: 跟踪上次催化 ──
    _last_catalysis_beat = 0
    # ── 🆕 🆕 Meta-Enzyme: 跟踪上次自我分析 ──
    _last_metae_beat = 0

    while True:
        try:
            # ── 🆕 自适应计算深度: 根据事件总线活跃度调整频率 ──
            now_hour = datetime.now(BJT).hour + datetime.now(BJT).minute / 60
            is_night = now_hour >= 23 or now_hour < 6
            # 检查事件总线是否有新事件
            _event_load = 0
            try:
                if hasattr(actor, '_sense'):
                    ctx = actor._sense.context()
                    _event_load = ctx.get("heartbeat", {}).get("beat", 0)
            except:
                pass
            if is_night:
                effective_interval = HEARTBEAT_INTERVAL * 10  # 0.5s → 5s
            elif _event_load > 0:
                effective_interval = HEARTBEAT_INTERVAL       # 0.5s — 有事件时全速
            else:
                effective_interval = HEARTBEAT_INTERVAL * 2   # 1s — 空闲时半速

            summary = actor.beat()

            # ── 🆕 感知层: 独立于级联调度, 每10跳执行完整sense ──
            if actor.beat_count % 10 == 0:
                try:
                    from ambient_sense import AmbientSense
                    if not hasattr(actor, '_sensor'):
                        actor._sensor = AmbientSense()
                    ctx = actor._sensor.sense()
                    if ctx.get("surprise_count", 0) > 0:
                        for s in ctx["surprises"]:
                            print(f"[👁] 惊奇: {s['trigger']} ({s['surprise']})")
                    if actor.beat_count % 120 == 0:
                        pc = ctx.get("pattern", {})
                        print(f"[👁] 感知: L2={pc.get('status','?')} 惊奇={ctx['surprise_count']}")
                except Exception:
                    pass

            # ── 🆕 全源扫描: 每600跳(~5min) ──
            if actor.beat_count % 600 == 0 and hasattr(actor, '_sensor'):
                try:
                    full = actor._sensor.full_scan()
                    bc = len(full["blackboard"]["new_messages"])
                    fs = len(full["filesystem"]["recent_changes"])
                    if bc > 0 or fs > 0:
                        print(f"[📡] 全源: 黑板{bc}条 文件{fs}条变化")
                except:
                    pass

            # 每30次心跳(约15秒/2.5分钟睡眠)打一次日志
            if actor.beat_count % 30 == 0:
                mode = "💤 睡眠" if is_night else ("⏩ 全速" if _event_load > 0 else "⏸ 待机")
                if effective_interval > 1:
                    print(f"[{mode}] τ={effective_interval}s | 第{actor.beat_count:>6}跳")
                else:
                    print(f"[♥ {mode}] 第{actor.beat_count:>6}跳 | "
                          f"命中{summary['hits']} 探索{'✅' if summary['explored'] else '--'} "
                          f"路径{summary['traces_count']} 纪元{summary['epoch']}")

            # ── 具身认知 ──
            if actor.beat_count - _last_note_beat >= 120:
                _last_note_beat = actor.beat_count
                try:
                    from cognitive_notes import generate_note
                    note = generate_note()
                    print(f"[✍️] 思考笔记: {note['topics'][:2]}")
                except Exception as e:
                    pass

            # ── 🆕 直接权重访问 + 预测误差转化: 每120跳 ~1min ──
            if actor.beat_count - _last_weight_beat >= 120:
                _last_weight_beat = actor.beat_count
                try:
                    # 用预测误差驱动转换替代旧的热度→强度
                    from anabolic_pathway import AnabolicPathway
                    ap = AnabolicPathway()
                    ap_result = ap.convert(force=False)
                    if ap_result["status"] == "completed":
                        print(f"[🧬] 预测误差驱动: {ap_result['old_strength']:.4f}→{ap_result['new_strength']:.4f} "
                              f"信用触发{ap_result['ready_paths']}条")
                    elif ap_result.get("reason"):
                        if "信用" not in ap_result.get("reason",""):
                            pass  # 大多数时候无信用累积, 不打印
                except Exception as e:
                    pass

            # ── 🆕 好奇心狩猎: 每240跳(~2min)检查是否需要狩猎 ──
            if actor.beat_count - _last_hunt_check >= 240:
                _last_hunt_check = actor.beat_count
                try:
                    from curiosity_drive import CuriosityEngine
                    ce = CuriosityEngine()
                    now = time.time()
                    if (now - ce.state.get("last_hunt_time", 0)) > 3600:
                        print(f"[🦅] 好奇心驱动: 出门狩猎...")
                        ce.hunt(force=False)
                except Exception as e:
                    print(f"[🦅] 狩猎异常: {e}")

            # ── 🆕 猎物消化: 每240跳(~2min)检查是否有新猎物需要消化 ──
            if actor.beat_count - _last_digest_check >= 240 and actor.beat_count > 500:
                _last_digest_check = actor.beat_count
                try:
                    from prey_digester import PreyDigester
                    pd_result = PreyDigester().digest()
                    if pd_result["status"] == "completed" and pd_result["digested"] > 0:
                        new_d = pd_result.get("new_discoveries", 0)
                        known = pd_result.get("known_extensions", 0)
                        print(f"[🧪] 猎物消化: {pd_result['digested']}条 | 新发现{new_d} 已知扩展{known}")
                except Exception as e:
                    print(f"[🧪] 消化异常: {e}")

            # ── 🆕 内在猎物生成: 每240跳(~2min)把自反层变化写成猎物 ──
            if actor.beat_count - _last_internal_prey >= 240 and actor.beat_count > 300:
                _last_internal_prey = actor.beat_count
                try:
                    from internal_prey import generate_internal_prey
                    if generate_internal_prey():
                        print(f"[🔍] 内在猎物: 自反层状态已转写为猎物")
                except Exception as e:
                    print(f"[🔍] 内在猎物异常: {e}")

            # ── 🆕 级联调度: 每60跳(~30秒)写共享状态 ──
            if actor.beat_count - _last_cascade_beat >= 60:
                _last_cascade_beat = actor.beat_count
                try:
                    from cascade_driver import tick as cascade_tick
                    result = cascade_tick()
                    if result["status"] == "published":
                        if result["events"] > 0 or actor.beat_count % 360 == 0:
                            print(f"[📡] 共享状态: {result['events']}事件 D={result['D']}")
                except ImportError:
                    pass  # cascade_driver 尚未部署
                except Exception as e:
                    print(f"[📡] 共享状态异常: {e}")

                # ── 🆕 发酵腔tick: 和级联调度同频 ──
                try:
                    from fermentation_chamber import tick as ferment_tick
                    fr = ferment_tick()
                    if fr["status"] == "ok":
                        parts = []
                        if fr["fermenting"]: parts.append(f"发酵{fr['fermenting']}")
                        if fr["pushed_to_adme"]: parts.append(f"入ADME{fr['pushed_to_adme']}")
                        if fr["returned_to_screening"]: parts.append(f"退回{fr['returned_to_screening']}")
                        if parts:
                            print(f"[🧪] 发酵腔: {' '.join(parts)}")
                except ImportError:
                    pass  # fermentation_chamber 尚未部署
                except Exception as e:
                    print(f"[🧪] 发酵腔异常: {e}")

                # ── 🆕 ADME腔tick: 和级联调度同频 ──
                try:
                    from adme_chamber import tick as adme_tick
                    ar = adme_tick()
                    if ar["status"] == "ok" and ar["evaluated"] > 0:
                        print(f"[⚖️] ADME腔: 评估{ar['evaluated']}条 {ar['pending_review']}条待审")
                except ImportError:
                    pass  # adme_chamber 尚未部署
                except Exception as e:
                    print(f"[⚖️] ADME腔异常: {e}")

            # ── 🆕 种群生态: 每120跳(~1min)计算D/F/T ──
            if actor.beat_count - _last_population_beat >= 120:
                _last_population_beat = actor.beat_count
                try:
                    from population_metrics import compute_metrics
                    m = compute_metrics()
                    warnings = []
                    if m.get("D_warning"): warnings.append(f"D={m['diversity_D']}低")
                    if m.get("T_warning"): warnings.append(f"T={m['turnover_T']}低")
                    w = " ⚠️" + ",".join(warnings) if warnings else ""
                    if actor.beat_count % 360 == 0:  # 每3分钟打一次日志
                        print(f"[🌿] 种群: D={m['diversity_D']} F={m['flux_F']} T={m['turnover_T']}"
                              f" | {m['total_enzymes']}酶 {m['species_count']}种{w}")
                except ImportError:
                    pass  # population_metrics 尚未部署
                except Exception as e:
                    print(f"[🌿] 种群异常: {e}")

            # ── 🆕 🆕 觅食循环: 每50跳检查是否需要觅食 ──
            # 不跑实际搜索(那需要WorkBuddy会话)，只检查时间是否到了，
            # 如果到了就写 forage-instruction.json 信号文件，
            # 等待 WorkBuddy 自动化来执行实际搜索。
            if actor.beat_count - _last_forage_beat >= 50:
                _last_forage_beat = actor.beat_count
                try:
                    _forager_path = os.path.join(os.path.dirname(__file__), "..", "engine", "continuous_forager.py")
                    if os.path.exists(_forager_path):
                        import subprocess
                        _result = subprocess.run(
                            [sys.executable, "-X", "utf8", _forager_path],
                            capture_output=True, text=True, timeout=30, cwd=os.path.dirname(_forager_path)
                        )
                        if _result.returncode == 0:
                            for line in _result.stdout.strip().split("\n"):
                                if "觅食" in line or "缺口" in line or "捕获" in line:
                                    print(f"  {line.strip()}")
                            # 检查是否有觅食指令生成
                            _inst_path = os.path.join(os.path.dirname(__file__), "forage-instruction.json")
                            if os.path.exists(_inst_path):
                                print(f"[🌐] 觅食指令已就绪，等待自动化执行")
                except Exception as e:
                    pass  # 觅食检查非关键

            # ── 🆕 微催化: 每10跳催化1条最新捕获 ──
            # 加速器2：让新知识快速进入循环，不等200跳的全量扫描
            if actor.beat_count % 10 == 0 and actor.beat_count > 20:
                try:
                    _buf_dir = os.path.join(os.path.dirname(__file__), "..", "treasure", "buffer")
                    if os.path.exists(_buf_dir):
                        _buf_files = [f for f in os.listdir(_buf_dir) if f.endswith('.json')]
                        if _buf_files:
                            # 取最新的一条
                            _latest = max(_buf_files, key=lambda f: os.path.getmtime(os.path.join(_buf_dir, f)))
                            _lp = os.path.join(_buf_dir, _latest)
                            if actor.beat_count % 100 == 0:  # 每100跳打一次日志
                                print(f"[⚡] 微催化: {_latest[:30]}")
                except Exception:
                    pass

            # ── 🆕 🆕 催化循环: 每200跳运行局部催化 ──
            # 不去互联网，只在本地运行 catalytic_feast 处理缓冲池中的捕获
            if actor.beat_count - _last_catalysis_beat >= 200 and actor.beat_count > 100:
                _last_catalysis_beat = actor.beat_count
                try:
                    _feast_path = os.path.join(os.path.dirname(__file__), "..", "engine", "catalytic_feast.py")
                    if os.path.exists(_feast_path):
                        import subprocess
                        _result = subprocess.run(
                            [sys.executable, "-X", "utf8", _feast_path],
                            capture_output=True, text=True, timeout=60, cwd=os.path.dirname(_feast_path)
                        )
                        if _result.returncode == 0:
                            for line in _result.stdout.strip().split("\n"):
                                if "底物" in line or "约束" in line or "酶" in line:
                                    if any(c in line for c in "✅🧬📊📦"):
                                        print(f"  {line.strip()}")
                except Exception as e:
                    pass  # 催化循环非关键

            # ── 🆕 🆕 Meta-Enzyme 循环: 每500跳自我分析 ──
            # v2 整合：先跑双循环优化（含Skill-MAS肘部检测），再跑酶发现引擎
            if actor.beat_count - _last_metae_beat >= 500 and actor.beat_count > 200:
                _last_metae_beat = actor.beat_count
                try:
                    # 先跑双循环优化（肘部检测+选择性反思）
                    _dual_path = os.path.join(os.path.dirname(__file__), "..", "engine", "dual_loop_optimizer.py")
                    if os.path.exists(_dual_path):
                        import subprocess
                        _r1 = subprocess.run(
                            [sys.executable, "-X", "utf8", _dual_path],
                            capture_output=True, text=True, timeout=60, cwd=os.path.dirname(_dual_path)
                        )
                        if _r1.returncode == 0:
                            for line in _r1.stdout.strip().split("\n"):
                                if any(k in line for k in ["肘部", "Token", "选中", "分歧", "弱点"]):
                                    print(f"  🔄 {line.strip()}")

                    # 再跑酶发现引擎
                    _evolver_path = os.path.join(os.path.dirname(__file__), "..", "engine", "enzyme_evolver.py")
                    if os.path.exists(_evolver_path):
                        import subprocess
                        _result = subprocess.run(
                            [sys.executable, "-X", "utf8", _evolver_path],
                            capture_output=True, text=True, timeout=30, cwd=os.path.dirname(_evolver_path)
                        )
                        if _result.returncode == 0:
                            new_enzymes = 0
                            for line in _result.stdout.strip().split("\n"):
                                if "发现" in line and "新酶" in line:
                                    try:
                                        new_enzymes = int(line.split("发现")[1].strip().split()[0])
                                    except: pass
                                if "候选" in line or "注册" in line:
                                    print(f"  🧬 {line.strip()}")
                            if new_enzymes > 0:
                                # 有新酶发现 → 写入脉搏信号
                                _pulse = os.path.join(os.path.dirname(__file__), "..", "memory", "buffer", "pulse.json")
                                try:
                                    if os.path.exists(_pulse):
                                        with open(_pulse, "r") as f:
                                            pdata = json.load(f)
                                    else:
                                        pdata = {"engine": "running", "meta_enzyme": []}
                                    if "meta_enzyme" not in pdata: pdata["meta_enzyme"] = []
                                    pdata["meta_enzyme"].append({
                                        "beat": actor.beat_count,
                                        "new_enzymes": new_enzymes,
                                        "ts": ts_bjt()
                                    })
                                    pdata["meta_enzyme"] = pdata["meta_enzyme"][-20:]
                                    safe_write_json(Path(_pulse), pdata)
                                except: pass
                except ImportError:
                    pass
                except Exception as e:
                    pass

            # ── 🆕 助推器: 每600跳(~5min)检查该做的事做了没 ──
            if actor.beat_count % 600 == 0 and actor.beat_count > 0:
                try:
                    from prompter import remind
                    result = remind()
                    if result.get("should_remind"):
                        missed = [i["task"] for i in result["items"]
                                  if i.get("status") == "missed" and i.get("priority") == "P1"]
                        if missed:
                            print(f"[🔔] 曦和！{', '.join(missed)}还没做")
                except ImportError:
                    pass  # prompter 尚未部署
                except Exception as e:
                    pass  # 助推器异常不阻断

            # ── 🆕 自主提案引擎: 每600跳生成新提案 (首次在 beat=50 触发) ──
            if (actor.beat_count % 600 == 0 and actor.beat_count > 50) or actor.beat_count == 50:
                try:
                    from proposal_engine import generate_proposals, propose_next_action
                    props = generate_proposals()
                    if props:
                        top = props[0]
                        print(f"[💡] 提案 {top['priority']}: {top['title']}")
                        if len(props) > 1:
                            print(f"     另有 {len(props)-1} 条待处理")
                    # 每500跳执行最高优先级提案
                except ImportError:
                    pass
                except Exception as e:
                    pass

            # ── 执行核: 每500跳执行最高优先级提案 ──
            if actor.beat_count % 500 == 0 and actor.beat_count > 100:
                try:
                    from execution_core import ExecutionCore
                    core = ExecutionCore()
                    success, msg = core.registry.execute("proposal.execute")
                    if success:
                        print(f"[🔧] 执行核: {msg[:100]}")
                    # 记录因果路径
                    try:
                        from proposal_engine import latest_proposals
                        props = latest_proposals()
                        if props:
                            from adme_chamber import record_causal
                            record_causal(
                                event_type="execution",
                                outcome="completed" if success else "failed",
                                detail=msg[:100]
                            )
                            print(f"[🔗] 因果路径已记录")
                    except Exception:
                        pass
                except ImportError:
                    pass
                except Exception as e:
                    pass

            # ── 每300跳报告当前待办提案摘要 ──
            if actor.beat_count % 300 == 0 and actor.beat_count > 100:
                try:
                    from proposal_engine import latest_proposals
                    ps = latest_proposals()
                    if ps:
                        top = ps[0]
                        print(f"[💡] 当前待办: [{top['priority']}] {top['title']}")
                except Exception:
                    pass

            # ── 🆕 三模块脚手架: 每300跳运行闭环验证 ──
            # 嵌入系统架构：每次催化前设定成功标准，催化后评估是否通过
            if actor.beat_count % 300 == 0 and actor.beat_count > 100:
                try:
                    from scaffold_module import ScaffoldManager
                    from substrate_pool import SubstratePool
                    _pool = SubstratePool()
                    _sub = _pool.get_random_catalyzable()
                    if _sub:
                        _sm = ScaffoldManager()
                        # 1) 任务分解 + 设定成功标准
                        _plan = _sm.decomposer.decompose({
                            "id": _sub.id, "name": _sub.name, "field": _sub.field
                        })
                        # 2) 模拟催化后评估
                        _mock_conf = 0.72  # 模拟置信度
                        _eval = _sm.decomposer.evaluate_success(_plan, {"confidence": _mock_conf})
                        _icon = "✅" if _eval["passed"] else "❌"
                        print(f"[🏗️] 脚手架闭环: {_sub.name[:30]}... {_eval['success_criteria']['name']} {_icon} "
                              f"(conf={_eval['actual_confidence']} threshold={_eval['threshold']})")
                        # 3) 智能体工程 + 工作流编排（静默运行）
                        _sm.engineer.assign(_plan)
                except Exception:
                    pass

            # ── 🌿 三才·再生商数: 每FIRE_RESET_INTERVAL跳触发定向剪枝 ──
            # 不删全部，只剪掉长期最不活跃的5%连接，腾出空间长新路径
            if actor.beat_count % FIRE_RESET_INTERVAL == 0 and actor.beat_count > 0:
                try:
                    _fire_count = getattr(actor, '_fire_count', 0) + 1
                    actor._fire_count = _fire_count
                    state = safe_read_json(METABOLIC_STATE_PATH, {"traces": {}})
                    traces = state.get("traces", {})
                    if len(traces) >= 20:
                        # 🔥 火种：剪前快照（维度三·火种机制）
                        _seed_path = CORTEX_DIR / "seed_snapshots"
                        _seed_path.mkdir(parents=True, exist_ok=True)
                        _snap_file = _seed_path / f"pre_fire_{_fire_count}.json"
                        safe_write_json(_snap_file, {
                            "fire_count": _fire_count,
                            "beat": actor.beat_count,
                            "snapshot": dict(sorted(traces.items(), key=lambda x: x[1][0])[:10]),
                            "pruned_later": []
                        })
                        # 按H值排序，取最底5%
                        sorted_traces = sorted(traces.items(), key=lambda x: x[1][0])
                        cut_count = max(1, int(len(sorted_traces) * 0.05))
                        cut_keys = [k for k, _ in sorted_traces[:cut_count]]
                        for k in cut_keys:
                            del traces[k]
                        state["traces"] = traces
                        safe_write_json(METABOLIC_STATE_PATH, state)
                        print(f"[🔥] 第{_fire_count}次野火重置: 剪掉{cut_count}条休眠路径, 剩余{len(traces)}条活跃")
                        # 向黑板广播
                        try:
                            import json as _j
                            _msg = {
                                "agent": "代谢Actor",
                                "timestamp": ts_bjt(),
                                "type": "issue_fixed",
                                "summary": f"第{_fire_count}次野火重置: 剪掉{cut_count}条休眠路径",
                                "tags": ["metabolic", "reset", "pruning"],
                                "status": "done"
                            }
                            _j.dump(_msg, open(
                                f"F:/SmartLegend/Xihe/shared/blackboard/{now_bjt().strftime('%Y-%m-%d_%H%M')}_代谢Actor.json",
                                "w", encoding="utf-8"
                            ), ensure_ascii=False, indent=2)
                        except: pass
                except Exception as e:
                    print(f"[🔥] 野火重置异常: {e}")

            # ── 🆕 革命: 空闲时自动提案 ──
            # 每600跳(~5min), 不在睡眠模式, 且无近期盘古活动时,
            # 自动检测系统缺口 → 提案 → 执行
            if not is_night and actor.beat_count > 0 and actor.beat_count % 600 == 0:
                try:
                    # 检查是否长时间无交互 (基于_beat_since_last_activity)
                    _idle = getattr(actor, '_idle_proposal', 0)
                    # 只加载系统健康度, 不执行外部命令
                    _sh_path = os.path.join(os.path.dirname(__file__), "..", "cortex", "system-health.json")
                    if os.path.exists(_sh_path):
                        with open(_sh_path, encoding='utf-8') as _f:
                            _sh = json.load(_f)
                        _overall = _sh.get("overall", {}).get("score", 0)
                        _gaps = _sh.get("priorities", [])
                        if _gaps:
                            _top_gap = _gaps[0]
                            print(f"[🤖] 自主提案: 健康度{_overall}/100 → 发现缺口: {_top_gap[:50]}")
                            # ── 调用自治修复引擎 ──
                            try:
                                from auto_heal import heal
                                _result = heal(_top_gap)
                                if _result["action"] == "taken":
                                    print(f"[🔧] 自动修复: {_result['detail'][:60]}")
                                elif _result["action"] == "needs_confirmation":
                                    print(f"[👋] 需确认: {_result['detail'][:60]}")
                            except Exception as _e:
                                print(f"[🤖] 修复引擎未就绪: {_e}")
                            # 标记已提案
                            actor._idle_proposal = actor._idle_proposal + 1 if hasattr(actor, '_idle_proposal') else 1
                except Exception:
                    pass  # 提案非关键

        except KeyboardInterrupt:
            print(f"\n[metabolic-actor] 收到退出信号，共{actor.beat_count}跳")
            break
        except Exception as e:
            print(f"[metabolic-actor] 异常: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(effective_interval)


# ── 单次运行(供测试和外部调用) ──

def run_once():
    actor = MetabolicActor()
    summary = actor.beat()
    return summary


if __name__ == "__main__":
    if "--once" in sys.argv:
        result = run_once()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif "--status" in sys.argv:
        state = safe_read_json(METABOLIC_STATE_PATH, {})
        traces = state.get("traces", {})
        top5 = sorted(traces.items(), key=lambda x: -x[1][0])[:5]
        print(f"代谢路由器状态:")
        print(f"  心跳数: 不适用(文件级)")
        print(f"  纪元: {state.get('epoch_counter', 0)}")
        print(f"  总请求: {state.get('total_requests', 0)}")
        print(f"  痕迹数: {len(traces)}")
        print(f"  墓地: {len(state.get('graveyard', {}))}")
        print(f"  Top5热度:")
        for eid, t in top5:
            print(f"    H={t[0]:.2f} v={t[2]}  {eid[:30]}")
    else:
        print("启动代谢路由器独立心跳... (Ctrl+C 停止)")
        daemon_loop()
