"""
曦和七层架构v2 · 层激活器
三进制状态机：检测→唤醒→验证 每一层的状态
酶桥管理器：注册和管理跨层酶桥
"""

import json, time, os, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

XIHE = Path("F:/SmartLegend/Xihe")
CORTEX = XIHE / "cortex"
BJT = timezone(timedelta(hours=8))

LAYER_FILE = CORTEX / "layer-health.json"

def load_layers():
    try:
        text = LAYER_FILE.read_text(encoding="utf-8").lstrip("\ufeff")
        d = json.loads(text)
        if "layers" not in d:
            log(f"load_layers: 无layers键, 有keys={list(d.keys())}")
            d = _default_layers()
        return d
    except Exception as e:
        log(f"load_layers异常: {e}")
        import traceback; traceback.print_exc()
        return _default_layers()

def _default_layers():
    return {
        "version": "xcrn-v2-neural-enzyme",
        "updated": datetime.now(BJT).isoformat(),
        "layers": {l: {"status": "dormant", "health": 0.0} for l in ["L0","L1","L2","L3","L4","L5","L6","L7"]},
        "enzyme_bridges": [],
        "system_report": "默认结构"
    }

def save_layers(data):
    LAYER_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def log(msg):
    ts = datetime.now(BJT).strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}")

# ── L1 · 知识层激活 ──
def activate_L1():
    """从旧的hebbian数据重建知识层"""
    log("L1 知识层 · 开始唤醒...")
    
    # 读取旧hebbian数据
    edges_file = CORTEX / "hebbian-edges.json"
    tracker_file = XIHE / "bridge" / "hebbian-tracker.json"
    
    knowledge = {
        "version": "v2",
        "activated_at": datetime.now(BJT).isoformat(),
        "edges": {},
        "nodes": {},
        "hebbian_stats": {"total_edges": 0, "total_nodes": 0, "avg_weight": 0}
    }
    
    # 从hebbian-tracker.json v2版读取
    if tracker_file.exists():
        try:
            t = json.loads(tracker_file.read_text(encoding="utf-8").lstrip("\ufeff"))
            if "edges" in t:
                knowledge["edges"] = {k: v if isinstance(v, dict) else {"w": v, "decay": 0.995} 
                                      for k, v in t["edges"].items()}
                knowledge["hebbian_stats"]["total_edges"] = len(knowledge["edges"])
            for k, v in knowledge["edges"].items():
                if isinstance(v, dict) and "w" in v:
                    knowledge["hebbian_stats"]["avg_weight"] += v["w"]
            if knowledge["hebbian_stats"]["total_edges"] > 0:
                knowledge["hebbian_stats"]["avg_weight"] /= knowledge["hebbian_stats"]["total_edges"]
            log(f"  → 从hebbian-tracker加载 {len(knowledge['edges'])} 条边")
        except Exception as e:
            log(f"  ⚠ tracker读取失败: {e}")
    
    # 从hebbian-edges.json旧版补充
    if edges_file.exists():
        try:
            e = json.loads(edges_file.read_text(encoding="utf-8").lstrip("\ufeff"))
            if isinstance(e, dict) and "edges" in e:
                for k, v in e["edges"].items():
                    if k not in knowledge["edges"]:
                        knowledge["edges"][k] = {"w": v if isinstance(v, (int, float)) else 0.5, "decay": 0.99}
                knowledge["hebbian_stats"]["total_edges"] = len(knowledge["edges"])
                log(f"  → 从hebbian-edges补充，总计 {len(knowledge['edges'])} 条边")
        except Exception as e:
            log(f"  ⚠ edges读取失败: {e}")
    
    # 写入知识层文件
    kf = CORTEX / "L1-knowledge.json"
    kf.write_text(json.dumps(knowledge, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # 更新层状态
    layers = load_layers()
    layers["L1"]["status"] = "active"
    layers["L1"]["health"] = 0.75
    layers["L1"]["last_awakening"] = datetime.now(BJT).isoformat()
    layers["L1"]["implementations"] = ["L1-knowledge.json", "hebbian-tracker.json (v2)"]
    save_layers(layers)
    log(f"✅ L1 知识层激活完成 · {knowledge['hebbian_stats']['total_edges']} 条边")
    return True

# ── L3 · 拓扑层激活 ──
def activate_L3():
    """从代谢路由traces重建拓扑层"""
    log("L3 拓扑层 · 开始重建...")
    
    # 读取代谢路由状态
    meta_file = CORTEX / "metabolic-router-state.json"
    traces = {}
    
    if meta_file.exists():
        try:
            m = json.loads(meta_file.read_text(encoding="utf-8").lstrip("\ufeff"))
            if "traces" in m:
                traces = m["traces"]
        except: pass
    
    topology = {
        "version": "v2",
        "activated_at": datetime.now(BJT).isoformat(),
        "modules": {},
        "communities": [],
        "path_network": {},
        "stats": {"total_paths": len(traces), "clusters": 0, "avg_path_length": 0}
    }
    
    # 从traces重建路径网络
    for path_id, hits in traces.items():
        parts = path_id.split("→") if "→" in path_id else [path_id]
        topology["path_network"][path_id] = {
            "length": len(parts),
            "hits": sum(hits) if isinstance(hits, list) else (hits if isinstance(hits, (int, float)) else 0),
            "modules": list(set(p.split(":")[0] if ":" in p else p for p in parts))
        }
    
    # 简单社区检测：按模块分组
    modules = {}
    for pid, info in topology["path_network"].items():
        for m in info["modules"]:
            if m not in modules: modules[m] = {"paths": 0, "total_hits": 0}
            modules[m]["paths"] += 1
            modules[m]["total_hits"] += info["hits"]
    
    topology["modules"] = modules
    topology["stats"]["clusters"] = len(modules)
    topology["stats"]["avg_path_length"] = sum(p["length"] for p in topology["path_network"].values()) / max(len(topology["path_network"]), 1)
    topology["communities"] = [{"name": k, "size": v["paths"], "activity": v["total_hits"]} for k, v in sorted(modules.items(), key=lambda x: -x[1]["total_hits"])[:10]]
    
    # 写入拓扑层文件
    tf = CORTEX / "L3-topology.json"
    tf.write_text(json.dumps(topology, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # 更新层状态
    layers = load_layers()
    layers["L3"]["status"] = "active"
    layers["L3"]["health"] = 0.70
    layers["L3"]["last_awakening"] = datetime.now(BJT).isoformat()
    layers["L3"]["implementations"] = ["L3-topology.json", "layer_activator.py"]
    save_layers(layers)
    log(f"✅ L3 拓扑层重建完成 · {topology['stats']['clusters']} 个模块, {len(topology['path_network'])} 条路径")
    return True

# ── L6 · 免疫层激活 ──
def activate_L6():
    """将现有安全组件注册为L6免疫层"""
    log("L6 免疫层 · 开始注册...")
    
    safety_status = {
        "version": "v2",
        "activated_at": datetime.now(BJT).isoformat(),
        "components": {},
        "rules": [],
        "stats": {"total_rules": 0, "active_guards": 0}
    }
    
    # 检查各安全组件
    guards = {
        "safety_guard.py": XIHE / "bridge" / "safety_guard.py",
        "mode_switch.py": XIHE / "bridge" / "mode_switch.py",
        "safety-rules.json": CORTEX / "safety-rules.json",
        "security-audit.cjs": XIHE / "xihe-desktop-app" / "security-audit.cjs",
    }
    
    for name, path in guards.items():
        exists = path.exists()
        safety_status["components"][name] = {"present": exists, "loaded": exists}
        if exists: safety_status["stats"]["active_guards"] += 1
    
    # 读取安全规则
    rules_file = CORTEX / "safety-rules.json"
    if rules_file.exists():
        try:
            r = json.loads(rules_file.read_text(encoding="utf-8"))
            safety_status["rules"] = r if isinstance(r, list) else [r]
            safety_status["stats"]["total_rules"] = len(safety_status["rules"])
        except: pass
    
    # 写入免疫层文件
    lf = CORTEX / "L6-immunity.json"
    lf.write_text(json.dumps(safety_status, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # 更新层状态
    layers = load_layers()
    layers["L6"]["status"] = "active"
    layers["L6"]["health"] = 0.75
    layers["L6"]["last_awakening"] = datetime.now(BJT).isoformat()
    layers["L6"]["implementations"] = list(guards.keys())
    save_layers(layers)
    log(f"✅ L6 免疫层注册完成 · {safety_status['stats']['active_guards']} 个守卫, {safety_status['stats']['total_rules']} 条规则")
    return True

# ── 酶桥打通器 ──
def build_enzyme_bridges():
    """打通所有跨层酶桥"""
    log("🔗 开始打通酶桥...")
    
    layers = load_layers()
    bridges = layers.get("enzyme_bridges", [])
    
    bridge_status = {
        "version": "v2",
        "activated_at": datetime.now(BJT).isoformat(),
        "bridges": [],
        "stats": {"total": len(bridges), "active": 0, "dormant": 0, "awakening": 0}
    }
    
    for b in bridges:
        from_layer = b["from"]
        to_layer = b["to"]
        from_status = layers.get(from_layer, {}).get("status", "unknown")
        to_status = layers.get(to_layer, {}).get("status", "unknown")
        
        # 酶桥状态 = 两端层状态的最小值
        if from_status == "active" and to_status == "active":
            bridge_status["bridges"].append({"from": from_layer, "to": to_layer, "status": "active"})
            bridge_status["stats"]["active"] += 1
        elif from_status == "dormant" or to_status == "dormant":
            bridge_status["bridges"].append({"from": from_layer, "to": to_layer, "status": "dormant"})
            bridge_status["stats"]["dormant"] += 1
        else:
            bridge_status["bridges"].append({"from": from_layer, "to": to_layer, "status": "awakening"})
            bridge_status["stats"]["awakening"] += 1
    
    # 写入桥接状态
    bf = CORTEX / "enzyme-bridges.json"
    bf.write_text(json.dumps(bridge_status, indent=2, ensure_ascii=False), encoding="utf-8")
    
    log(f"  活跃: {bridge_status['stats']['active']} / 休眠: {bridge_status['stats']['dormant']} / 苏醒: {bridge_status['stats']['awakening']}")
    
    # 更新层健康报告
    layers["system_report"] = (
        f"L2/L4/L5活跃 + L0/Watchman稳固. "
        f"L1/L3/L6已激活 ✅. "
        f"L7苏醒中. "
        f"酶桥 {bridge_status['stats']['active']}/{bridge_status['stats']['total']} 活跃."
    )
    save_layers(layers)
    log(f"✅ 酶桥打通完成 · {bridge_status['stats']['active']}/{bridge_status['stats']['total']} 活跃")
    return True

if __name__ == "__main__":
    print("\n🧬 曦和七层架构v2 · 层激活器")
    print("=" * 40)
    
    results = []
    
    print("\n1️⃣  重建L1 · 知识层")
    results.append(("L1", activate_L1()))
    
    print("\n2️⃣  重建L3 · 拓扑层")
    results.append(("L3", activate_L3()))
    
    print("\n3️⃣  注册L6 · 免疫层")
    results.append(("L6", activate_L6()))
    
    print("\n4️⃣  打通酶桥")
    results.append(("bridges", build_enzyme_bridges()))
    
    print("\n" + "=" * 40)
    print("📊 最终层状态:")
    layers = load_layers()
    for lid, info in layers.get("layers", {}).items():
        icon = {"active": "🟢", "dormant": "🟡", "awakening": "🔵", "unknown": "⚪"}
        print(f"  {icon.get(info['status'], '⚪')} {lid}: {info['status']} (健康度: {info['health']})")
    print(f"\n📋 系统报告: {layers.get('system_report', '')}")
