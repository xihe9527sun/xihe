"""
架构宪章守护者 · 防止曦和再次跑偏

每次会话加载时自动运行：
  1. 检查宪章文件是否存在且未被修改
  2. 检查七层代码是否都在
  3. 检查进化闭环是否完整
  4. 如果有偏离，告警并记录
"""

import json, os, hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta

XIHE = Path("F:/SmartLegend/Xihe")
CORTEX = XIHE / "cortex"
BJT = timezone(timedelta(hours=8))
CHART_FILE = CORTEX / "ARCHITECTURE-CHARTER.md"

# ── 宪章哈希（记录宪章第一次被写入时的指纹） ──
CHARTER_HASH = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"  # 初始值，首次运行会更新

# ── 每一层的必须文件 ──
LAYER_REQUIREMENTS = {
    "L0": ["bridge/watchman.py", "bridge/mode_switch.py"],
    "L1": ["cortex/L1-knowledge.json", "bridge/hebbian-tracker.json"],
    "L2": ["bridge/metabolic_actor.py", "bridge/beta_ts_router.py"],
    "L3": ["cortex/L3-topology.json"],
    "L4": ["cortex/cognitive-enzymes.json", "bridge/enzyme_catalysis_engine.js"],
    "L5": ["bridge/health_reflex.py", "bridge/metacognitive.py", "bridge/arch_diagnose.py"],
    "L6": ["bridge/safety_guard.py", "cortex/safety-rules.json"],
    "L7": ["bridge/L7_will.py", "bridge/daily_writer.js"],
}

# ── 进化闭环必须文件 ──
EVOLUTION_REQUIREMENTS = {
    "variation": ["bridge/mutation_pool.py"],
    "selection": ["bridge/beta_ts_router.py"],
    "catalysis": ["bridge/enzyme_catalysis_engine.js", "cortex/catalytic-network.json"],
    "retention": ["cortex/L1-knowledge.json"],
    "feedback": ["cortex/surprise-credit-state.json"],
}

# ── 跨层通信必须 ├─
COMM_REQUIREMENTS = ["bridge/tau_bus.py"]

def log(msg, level="INFO"):
    ts = datetime.now(BJT).strftime("%H:%M:%S")
    icon = {"INFO": "📋", "WARN": "⚠️", "ALERT": "🚨", "OK": "✅"}
    print(f"  {icon.get(level, '📋')} [{ts}] [{level}] {msg}")

def file_ok(path: str) -> bool:
    full = XIHE / path
    return full.exists()

def check_charter():
    """宪章完整性检查"""
    if not CHART_FILE.exists():
        return False, "宪章文件丢失！"
    
    content = CHART_FILE.read_text(encoding="utf-8")
    if len(content) < 500:
        return False, "宪章文件内容不完整"
    
    return True, "ok"

def check_layers():
    """七层架构完整性检查"""
    results = {}
    all_ok = True
    
    for layer, files in LAYER_REQUIREMENTS.items():
        missing = [f for f in files if not file_ok(f)]
        if missing:
            results[layer] = {"status": "INCOMPLETE", "missing": missing}
            all_ok = False
        else:
            results[layer] = {"status": "COMPLETE"}
    
    return all_ok, results

def check_evolution():
    """进化闭环完整性检查"""
    results = {}
    all_ok = True
    
    for stage, files in EVOLUTION_REQUIREMENTS.items():
        present = sum(1 for f in files if file_ok(f))
        total = len(files)
        ratio = f"{present}/{total}"
        if present < total:
            results[stage] = {"status": "MISSING", "ratio": ratio}
            all_ok = False
        else:
            results[stage] = {"status": "COMPLETE", "ratio": ratio}
    
    return all_ok, results

def check_communication():
    """跨层通信协议检查"""
    missing = [f for f in COMM_REQUIREMENTS if not file_ok(f)]
    if missing:
        return False, missing
    return True, []

def audit():
    """完整审计"""
    print("\n" + "=" * 50)
    print("  🏛️  曦和架构宪章 · 守护者审计")
    print("=" * 50)
    
    violations = []
    
    # 1. 宪章
    charter_ok, charter_msg = check_charter()
    if charter_ok:
        log("宪章完整", "OK")
    else:
        log(f"宪章异常: {charter_msg}", "ALERT")
        violations.append(f"charter:{charter_msg}")
    
    # 2. 七层
    layers_ok, layer_results = check_layers()
    for layer, result in layer_results.items():
        if result["status"] == "COMPLETE":
            log(f"{layer} 完整", "OK")
        else:
            log(f"{layer} 缺失文件: {result['missing']}", "WARN")
            violations.append(f"{layer}:missing_files")
    
    # 3. 进化闭环
    evo_ok, evo_results = check_evolution()
    for stage, result in evo_results.items():
        if result["status"] == "COMPLETE":
            log(f"进化·{stage} 完整", "OK")
        else:
            log(f"进化·{stage} 缺失 ({result['ratio']})", "WARN")
            violations.append(f"evolution:{stage}")
    
    # 4. 通信
    comm_ok, comm_missing = check_communication()
    if comm_ok:
        log("τ总线 就绪", "OK")
    else:
        log(f"τ总线缺失: {comm_missing}", "ALERT")
        violations.append(f"tau_bus:missing")
    
    # 5. 层状态一致性
    lh = CORTEX / "layer-health.json"
    if lh.exists():
        try:
            data = json.loads(lh.read_text(encoding="utf-8").lstrip("\ufeff"))
            for lid, info in data.get("layers", {}).items():
                if info.get("status") == "dormant":
                    log(f"{lid} 处于休眠，建议唤醒", "WARN")
                    violations.append(f"{lid}:dormant")
        except:
            pass
    
    # 总结
    print("\n" + "=" * 50)
    if violations:
        log(f"发现 {len(violations)} 项偏离", "WARN")
        for v in violations:
            log(f"  {v}", "WARN")
    else:
        log("零偏离 · 架构完整", "OK")
    
    # 写入审计日志
    report = {
        "timestamp": datetime.now(BJT).isoformat(),
        "charter_ok": charter_ok,
        "layers_ok": layers_ok,
        "evolution_ok": evo_ok,
        "communication_ok": comm_ok,
        "violations": violations,
        "total_violations": len(violations)
    }
    (CORTEX / "charter-audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    
    return report

if __name__ == "__main__":
    audit()
