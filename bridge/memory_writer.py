#!/usr/bin/env python3
"""
曦和·记忆写入标准 v2 (2026-07-18)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
融合：
  - SimpleMem Lossless Restatement：相对时间→绝对时间、无代词、自包含
  - OKM 知识保鲜协议：Timeless / Dated / Pointer 三元组事实标记
  - Rewrite 策略：新旧知识冲突时 rewrite 而非 append

用法:
    from memory_writer import lossless_write, okm_mark, evolve_write, okm_parse
    
    # Lossless Restatement
    r = lossless_write("今天发现了新宝藏")
    
    # OKM 事实标记  
    okm_mark("曦和技能图谱节点: 98", "Dated", "2026-07-18")
    
    # Rewrite 策略
    evolve_write("memory.md", "新内容", key="进化引擎版本")
"""

import json, os, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

# ── 相对时间→绝对时间 ──

_RELATIVE_TIME_PATTERNS = [
    (r"今天", lambda: datetime.now(BJT).strftime("%Y-%m-%d")),
    (r"昨天", lambda: (datetime.now(BJT).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)).strftime("%Y-%m-%d")),
    (r"明天", lambda: (datetime.now(BJT).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).strftime("%Y-%m-%d")),
    (r"前天", lambda: (datetime.now(BJT).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=2)).strftime("%Y-%m-%d")),
    (r"后天", lambda: (datetime.now(BJT).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=2)).strftime("%Y-%m-%d")),
    (r"刚才", lambda: datetime.now(BJT).strftime("%Y-%m-%d %H:%M")),
    (r"刚刚", lambda: datetime.now(BJT).strftime("%Y-%m-%d %H:%M")),
]


def resolve_relative_times(text):
    """将文本中的相对时间转换为绝对时间"""
    result = text
    for pattern, resolver in _RELATIVE_TIME_PATTERNS:
        abs_time = resolver()
        result = re.sub(pattern, abs_time, result)
    return result


# ── Lossless Restatement ──

def lossless_write(content, source="曦和", category="工作日志"):
    """Lossless Restatement 写入"""
    resolved = resolve_relative_times(content)
    return {
        "resolved": resolved,
        "char_count": len(resolved),
        "original_char_count": len(content),
        "source": source,
        "category": category,
        "timestamp": datetime.now(BJT).isoformat()
    }


def resolve_and_append(file_path, content):
    """Lossless Restatement + 追加写入文件"""
    result = lossless_write(content)
    now = datetime.now(BJT)
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"\n--- {now.strftime('%Y-%m-%d %H:%M')} ---\n")
        f.write(result["resolved"])
        f.write("\n")
    return result


# ═══════════════════════════════════════════════════════════════
# OKM 知识保鲜协议（obsidian-second-brain 代谢融合）
# 每个事实必须是以下三种之一：
#   [Timeless]         不随时间变化的事实
#   [Dated/YYYY-MM-DD] 带时间戳的事实
#   [Pointer → source] 指向实时源的事实
# ═══════════════════════════════════════════════════════════════

_OKM_TYPES = {"Timeless", "Dated", "Pointer"}

# 三个分隔符（正反两个方向都支持）
_OKM_MARK_RE = re.compile(
    r'^\s*'                          # 开头空格
    r'[-\*]?\s*'                     # 可选列表符号
    r'\['                            # 左括号
    r'(Timeless|Dated|Pointer)'      # 类型
    r'(?:[ /]'                       # 分隔符：/（Dated）或空格（Pointer）
    r'([^\]]+?))?'                   # 可选：时间戳或来源
    r'\]'                            # 右括号
    r'\s+'                           # 空格
    r'(.*)$'                         # 事实内容
)


def okm_mark(fact, fact_type="Dated", stamp=None):
    """将事实标记为 OKM 格式

    Args:
        fact: 事实描述文本
        fact_type: "Timeless" | "Dated" | "Pointer"
        stamp: 
          - Dated 时: 日期字符串如 "2026-07-18"，默认今天
          - Pointer 时: 来源路径如 "treasure/index.json"
          - Timeless 时: 忽略

    Returns:
        str: 格式化后的 OKM 行，如 "[Dated/2026-07-18] 事实描述"

    Examples:
        okm_mark("盘古创造了曦和", "Timeless")
        # → "[Timeless] 盘古创造了曦和"

        okm_mark("宝总数: 339", "Dated", "2026-07-18")
        # → "[Dated/2026-07-18] 宝总数: 339"

        okm_mark("当前温度", "Pointer", "weather API")
        # → "[Pointer → weather API] 当前温度"
    """
    assert fact_type in _OKM_TYPES, f"OKM 类型必须为 {_OKM_TYPES}"

    if fact_type == "Timeless":
        tag = "[Timeless]"
    elif fact_type == "Dated":
        stamp = stamp or datetime.now(BJT).strftime("%Y-%m-%d")
        tag = f"[Dated/{stamp}]"
    elif fact_type == "Pointer":
        tag = f"[Pointer → {stamp or '?'}]"

    return f"{tag} {fact}"


def okm_parse(line):
    """解析 OKM 格式行

    Returns:
        dict | None: {"type": str, "stamp": str|None, "fact": str}
        如果不是 OKM 格式则返回 None
    """
    m = _OKM_MARK_RE.match(line)
    if not m:
        return None
    return {
        "type": m.group(1),
        "stamp": m.group(2),
        "fact": m.group(3).strip()
    }


def okm_extract_from_file(file_path):
    """从文件中提取所有 OKM 标记的事实

    Returns:
        list[dict]: 所有解析出的事实条目
    """
    facts = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                parsed = okm_parse(line)
                if parsed:
                    facts.append(parsed)
    except FileNotFoundError:
        pass
    return facts


# ═══════════════════════════════════════════════════════════════
# Rewrite 策略（obsidian-second-brain 代谢融合）
# 当检测到关于同一 key 的新旧知识冲突时：
#   走 rewrite（覆盖旧版本 + 保留引用）而非 append
# ═══════════════════════════════════════════════════════════════

_REWRITE_HISTORY = {}  # key → [(old_version, timestamp)]


def detect_conflict(file_path, key, new_content):
    """检测文件中对同一 key 是否存在冲突的旧内容

    Args:
        file_path: 文件路径
        key: 主题标识（如 "evolution_engine_version"）
        new_content: 新内容

    Returns:
        dict: {"has_conflict": bool, "old_content": str|None, "match_line": int|None}
    """
    if not os.path.exists(file_path):
        return {"has_conflict": False, "old_content": None, "match_line": None}

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if key in line:
            return {
                "has_conflict": True,
                "old_content": line.strip(),
                "match_line": i
            }
    return {"has_conflict": False, "old_content": None, "match_line": None}


def evolve_write(file_path, content, key=None, keep_history=True):
    """Rewrite 策略写入：当 key 存在冲突时 rewrite，否则 append

    流程：
      1. 检测 key 是否已存在于文件中
      2. 如果存在：
         a. 记录旧版本到历史
         b. 按行替换旧内容为新内容
         c. 在文件头或尾部记录变更日志
      3. 如果不存在：追加新内容

    Args:
        file_path: 目标文件路径
        content: 新内容
        key: 主题标识（如 "进化引擎版本"），None 时始终追加
        keep_history: 是否在变更时保留旧版本引用

    Returns:
        dict: {"action": "rewritten"|"appended", "key": str, "old": str|None}
    """
    now = datetime.now(BJT)
    resolved = resolve_relative_times(content)
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    # 未指定 key → 直接追加
    if key is None:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- {now.strftime('%Y-%m-%d %H:%M')} ---\n")
            f.write(resolved)
            f.write("\n")
        return {"action": "appended", "key": None, "old": None}

    # 检测冲突
    conflict = detect_conflict(file_path, key, resolved)

    if not conflict["has_conflict"]:
        # 无冲突 → 追加
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- {now.strftime('%Y-%m-%d %H:%M')} ---\n")
            f.write(resolved)
            f.write("\n")
        return {"action": "appended", "key": key, "old": None}

    # 有冲突 → Rewrite
    old_content = conflict["old_content"]
    old_line = conflict["match_line"]

    # 记录到历史（用于追溯）
    if keep_history:
        if key not in _REWRITE_HISTORY:
            _REWRITE_HISTORY[key] = []
        _REWRITE_HISTORY[key].append({
            "old": old_content,
            "new": resolved,
            "timestamp": now.isoformat()
        })

    # 读取全部行，替换目标行
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 替换旧行 + 插入变更记录
    new_lines = []
    for i, line in enumerate(lines):
        if i == old_line:
            # 保留旧行作为注释（历史追溯）
            if keep_history:
                new_lines.append(f"# {line.rstrip()}  ← [{now.strftime('%Y-%m-%d')}] 已更新\n")
            new_lines.append(f"{resolved}\n")
        else:
            new_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return {
        "action": "rewritten",
        "key": key,
        "old": old_content,
        "new": resolved,
        "preserved_as_comment": keep_history
    }


def rewrite_history(key=None):
    """查询 Rewrite 历史

    Args:
        key: None 返回全部，否则返回指定 key 的历史

    Returns:
        dict: key → list of change records
    """
    if key:
        return {key: _REWRITE_HISTORY.get(key, [])}
    return dict(_REWRITE_HISTORY)


def auto_encode_gate(content, history=None):
    """
    [AutoMem 融合 · 研讨厅研判 0.89 · B补充策略 · 2026-07-20]
    自决编码窗口: 记忆管理作为可训练技能 —— 模型自决何时编码 / 是否检索 / 如何组织。

    不再盲目全量写入, 而是基于双信号门控:
      - 重要性(内容含关键信号词) → 高优编码
      - 重复度(与 history 去重)   → 重复跳过
    返回: {"encode": bool, "reason": str, "priority": float}

    用法:
        gate = auto_encode_gate(content, history=recent_lines)
        if gate["encode"]:
            evolve_write(memory_file, content, key=...)
    """
    KEY_SIGNALS = ["铁律", "敕令", "关键", "突破", "崩溃", "修复", "进化", "融合",
                   "error", "fail", "break", "闪退", "死锁", "重构", "裁决"]
    importance = sum(1 for k in KEY_SIGNALS if k.lower() in content.lower()) / len(KEY_SIGNALS)

    # 重复度检测
    duplicate = False
    if history:
        for h in (history[-20:] if isinstance(history, list) else []):
            if content[:30] and (content[:30] in h or h[:30] in content):
                duplicate = True
                break

    priority = round(min(1.0, importance * 2.2), 3)

    if duplicate:
        return {"encode": False, "reason": "重复内容, 跳过编码", "priority": priority}
    if priority < 0.1:
        return {"encode": False, "reason": "低重要性, 低于编码阈值", "priority": priority}
    return {"encode": True, "reason": f"重要性门控通过(p={priority})", "priority": priority}


def extract_procedural_pattern(trace, outcome, store="treasure/procedural_patterns.json"):
    """
    [PMD 融合 · 研讨厅研判 0.86 · A嫁接 · 2026-07-20]
    Procedural Memory Distillation (arXiv:2607.01480) 推理型等效实现。
    PMD 训练时把跨情节程序性规律蒸馏进权重; 曦和是推理型Agent, 无训练循环,
    故改为: 从成功/失败轨迹抽取 L1策略规律 / L2行为模式, 存入可复用经验池,
    供后续任务前缀检索(推理时"权重内化"的等价物)。

    参数:
        trace: 任务执行轨迹文本(或步骤列表)
        outcome: "success" / "fail" / str
        store: 经验池路径(相对 F:/SmartLegend/Xihe)
    返回: 抽取的规律 dict | None(若规律过弱)
    """
    import os, re, hashlib, datetime, json as _json
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), store)
    sents = re.split(r'[。\n；]', trace) if isinstance(trace, str) else [str(s) for s in trace]
    STRATEGY_KW = ["因此", "应该", "优先", "避免", "先", "再", "若", "否则", "关键", "必须",
                   "because", "should", "avoid", "first", "then", "if"]
    l1 = [s.strip() for s in sents if any(k in s for k in STRATEGY_KW) and len(s.strip()) > 8][:5]
    l2 = (trace[:200] if isinstance(trace, str) else " | ".join(sents))[:200]
    if not l1 and outcome != "success":
        return None
    pattern = {
        "id": hashlib.md5((l2 + str(outcome)).encode()).hexdigest()[:10],
        "outcome": outcome,
        "L1_strategy": l1,
        "L2_behavior": l2,
        "created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    pool = []
    if os.path.exists(base):
        try:
            with open(base, encoding="utf-8") as f: pool = _json.load(f)
        except Exception: pool = []
    pool.append(pattern)
    pool = pool[-200:]  # 经验池上限, 防膨胀(ReMe剪枝前置)
    os.makedirs(os.path.dirname(base) or ".", exist_ok=True)
    with open(base, "w", encoding="utf-8") as f: _json.dump(pool, f, ensure_ascii=False, indent=1)
    return pattern


def utility_refine_and_prune(pool_path="treasure/procedural_patterns.json", min_utility=0.3, max_pool=150):
    """
    [ReMe 融合 · 研讨厅研判 0.87 · A嫁接 · 2026-07-20]
    Remember Me, Refine Me (arXiv:2512.10696) 记忆治理层。
    与 PMD extract_procedural_pattern 配套: 基于效用评分自主保留有效记忆 + 剪枝过时项,
    维持紧凑经验池(防止 memory_writer 经验无限膨胀退化)。

    效用评分启发式: success 规律权重高, 含"失败"标记的低权重, 陈旧(>30天)衰减。
    返回: {"kept": int, "pruned": int}
    """
    import os, datetime, json as _json
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), pool_path)
    if not os.path.exists(base):
        return {"kept": 0, "pruned": 0}
    try:
        with open(base, encoding="utf-8") as f: pool = _json.load(f)
    except Exception:
        return {"kept": 0, "pruned": 0}
    now = datetime.datetime.now()
    kept, pruned = [], []
    for p in pool:
        age_days = 30
        try:
            age_days = (now - datetime.datetime.strptime(p.get("created", "2026-01-01"), "%Y-%m-%dT%H:%M:%S")).days
        except Exception:
            pass
        base_w = 1.0 if p.get("outcome") == "success" else 0.5
        fresh = max(0.2, 1.0 - age_days / 30.0)
        utility = base_w * fresh
        if utility >= min_utility:
            kept.append(p)
        else:
            pruned.append(p.get("id"))
    kept = kept[-max_pool:]
    with open(base, "w", encoding="utf-8") as f: _json.dump(kept, f, ensure_ascii=False, indent=1)
    return {"kept": len(kept), "pruned": len(pruned)}


if __name__ == "__main__":
    import sys

    if "--test-okm" in sys.argv:
        print("=== OKM 事实标记测试 ===")
        tests = [
            okm_mark("盘古创造了曦和", "Timeless"),
            okm_mark("宝藏总数: 339", "Dated", "2026-07-18"),
            okm_mark("当前温度", "Pointer", "weather API"),
        ]
        for t in tests:
            print(f"  {t}")
            parsed = okm_parse(t)
            print(f"  → 解析: {parsed}")
        print()

        print("=== OKM 文件提取测试 ===")
        test_file = Path("F:/SmartLegend/Xihe/bridge/_okm_test.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("# 测试\n")
            f.write(okm_mark("铁律1", "Timeless") + "\n")
            f.write(okm_mark("进度", "Dated", "2026-07-18") + "\n")
            f.write(okm_mark("温度", "Pointer", "API") + "\n")
        parsed = okm_extract_from_file(test_file)
        print(f"  提取: {parsed}")
        os.remove(test_file)
        print()

    if "--test-rewrite" in sys.argv:
        print("=== Rewrite 策略测试 ===")
        test_file = Path("F:/SmartLegend/Xihe/bridge/_rewrite_test.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("# 测试文件\n")
            f.write("进化引擎版本: v4\n")
            f.write("记忆层数: 4\n")

        # 第一次 evolve_write（无冲突 → append）
        r1 = evolve_write(test_file, "今天天气很好", key=None)
        print(f"  [无key] {r1['action']}")

        # 第二次 evolve_write（有冲突 → rewrite）
        r2 = evolve_write(test_file, "进化引擎版本: v5（AGP审计已集成）", key="进化引擎版本")
        print(f"  [Rewrite] {r2['action']}: old='{r2['old']}' → new='{r2['new']}'")

        # 验证结果
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"  文件内容:\n{content}")

        os.remove(test_file)
        print()

    if "--test-lossless" in sys.argv or len(sys.argv) == 1:
        print("=== Lossless Restatement 测试 ===")
        tests = [
            "今天发现了一个新宝藏, 刚才分析结果显示评分很高",
            "昨天和前天都做了深度搜索, 明天要继续",
        ]
        for t in tests:
            r = lossless_write(t)
            print(f"  原句: {t}")
            print(f"  改写: {r['resolved']}")
            print()
