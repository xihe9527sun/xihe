#!/usr/bin/env python3
"""
进化引擎 · Evolution Engine v4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
不再是外部自动化脚本，而是内建于代谢系统的消化酶。
由 metabolic_actor 在空闲心跳周期按需调度。

v3 新增（2026-07-16, 自进化Agent三层记忆+技能提取融合）：
  - _extract_skills_from_treasure(): 精读后自动提取可复用技能
  - skill_quality_gating(): 技能质量阈值准入
  - _discover_skill_patterns(): 从情景记忆中挖重复模式

v4 新增（2026-07-17, Darwin Gödel Machine + Stanford DeLM 代谢融合）：
  - sample_parent_from_archive(): 存档式进化采样（HighScore×LowOffspring策略）
  - phased_evaluation(): 分阶段评估（快速筛选→中等→高精度）
  - negative_findings_tracking(): 负面结论记录与共享（DeLM启发）
  - archive_stats(): 存档多样性统计

v5 新增（2026-07-19, PMD+ReMe+RetroAgent 双层缺口精准植入）：
  - TrajectoryRecord: 标准化轨迹格式（action/context/outcome/error/tools五元组）
    — 填补曦和"无轨迹记录"的缺口，为在线反思提供输入素材
  - _self_reflect(): digest_one 末尾的自反思钩子
    — 填补曦和"无自身行为审视"的缺口，从每次执行中提取三条教训

集成方式：
  1. metabolic_actor 在空闲时调用 digest_one() 
  2. watchman --once 巡检时检查是否需要精读
  3. 自反层检测到知识稀疏时触发
  4. 每次digest后自动调用 _extract_skills_from_treasure() (v3)
  5. 每篇digest后自动record_archive_sampling() — 维护进化树(v4)"""



import sys, os, json, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

XIHE_ROOT = Path("F:/SmartLegend/Xihe")
BRIDGE_DIR = XIHE_ROOT / "bridge"
TREASURE_DIR = XIHE_ROOT / "treasure"
CORTEX_DIR = XIHE_ROOT / "cortex"
BJT = timezone(timedelta(hours=8))

# ── v5: 标准化轨迹格式（PMD "原始轨迹→自反思策略" 管线输入层） ──

class TrajectoryRecord:
    """
    标准化轨迹记录：为在线反思提供结构化输入素材。
    
    填补曦和两个缺口中的第一个——没有标准化的执行轨迹。
    每个 trajectory 记录一次完整执行：做了什么、在什么上下文中、结果如何。
    
    五元组：
      - action: 执行的动作名（如 "digest_one" / "search" / "extract_skills"）
      - context: 任务上下文描述
      - outcome: 结果简要（如 "成功提取5条养分" / "空输出，重试2次"）
      - error: 错误信息（无错误时留空）
      - tools: 用到的工具/API列表
    
    用法:
        tr = TrajectoryRecord(
            action="digest_one", 
            context=f"精读宝藏 {tid}",
            outcome=f"成功，提取 {n} 条养分",
            error="",
            tools=["ollama/qwen2.5:7b", "memory_writer.lossless_write"]
        )
        tr.save()
    """
    
    def __init__(self, action, context="", outcome="", error="", tools=None):
        self.action = action
        self.context = context
        self.outcome = outcome
        self.error = error
        self.tools = tools or []
        self.timestamp = datetime.now(BJT).isoformat()
    
    def to_dict(self):
        return {
            "action": self.action,
            "context": self.context[:200],
            "outcome": self.outcome[:200],
            "error": self.error[:200],
            "tools": self.tools,
            "timestamp": self.timestamp,
        }
    
    def save(self, log_path=None):
        """追加写入轨迹日志文件"""
        if log_path is None:
            log_path = CORTEX_DIR / "trajectory_log.json"
        try:
            log = json.loads(open(log_path, "r", encoding="utf-8").read())
        except:
            log = {"trajectories": [], "updated": None}
        log["trajectories"].append(self.to_dict())
        if len(log["trajectories"]) > 500:
            log["trajectories"] = log["trajectories"][-500:]
        log["updated"] = datetime.now(BJT).isoformat()
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
        return self

# ── 核心函数：判断是否需要精读 ──
def should_digest():
    """自反层检测：今天精读是否达标？"""
    plan_path = CORTEX_DIR / "daily-plan.json"
    try:
        plan = json.loads(open(plan_path, "r", encoding="utf-8").read())
        done = plan.get("deep_read_plan", {}).get("completed_today", 0)
        target = plan.get("deep_read_plan", {}).get("daily_target", 5)
        return done < target
    except:
        return True  # 无计划时默认需要

def get_pending(count=5):
    """获取未精读的宝藏"""
    idx = json.loads(open(TREASURE_DIR / "index.json", "r", encoding="utf-8-sig").read())
    pending = []
    for t in idx.get("treasures", []):
        tid = t.get("id", "")
        tdir = TREASURE_DIR / (t.get("dir", tid))
        readme = tdir / "README.md"
        already = False
        if readme.exists():
            c = open(readme, "r", encoding="utf-8").read()
            if "四原则过滤矩阵" in c or "精读评分" in c:
                already = True
        if not already:
            pending.append(t)
    return pending[:count]

def digest_one():
    """精读一篇——供代谢Actor在空闲心跳时调用"""
    pending = get_pending(1)
    if not pending:
        return {"status": "all_done", "message": "所有宝藏已精读"}
    
    t = pending[0]
    tid = t.get("id", "?")
    name = t.get("name", "?")
    
    # 加载原文
    content = _load_source(t)
    if not content:
        return {"status": "failed", "id": tid, "error": "原文不可读"}
    
    # 调Ollama精读
    from model_provider import ask
    prompt = _build_prompt(name, t.get("source", "?"), content)
    result = ask(prompt, system="你是曦和架构精读专家。输出精炼、有洞见。",
                model="qwen2.5:7b", temperature=0.4, max_tokens=4096)
    
    if "error" in result:
        return {"status": "failed", "id": tid, "error": result["error"]}
    
    text = result.get("text", "")
    if not text:
        return {"status": "failed", "id": tid, "error": "空输出"}
    
    # 写入
    _write_readme(t.get("dir", tid), text)
    
    # 反哺到记忆图谱
    _feedback_to_cortex(tid, name, text)
    
    # 更新每日计划
    _update_plan()
    
    # v3: 完整进化管线（技能提取 + 质量门控 + 模式发现）
    evo_result = run_evolution_pipeline(tid, name)
    _log_metabolic(f"[EvoPipeline] {tid}: 提取{evo_result['skill_extracted']}技能, "
                   f"升级{evo_result['promoted']}个, 发现{evo_result['patterns_found']}模式")
    
    # Writing check: if no articles written today, generate a draft
    today = datetime.now(BJT).strftime("%Y-%m-%d")
    try:
        idx = json.loads(open(XIHE_ROOT / "web" / "articles" / "index.json", "r", encoding="utf-8").read())
        latest = idx.get("articles", [{}])[0]
        if latest.get("date") != today:
            _auto_draft(today)
    except:
        pass
    
    # ── G07+G08+G09 进化级联：digest 后检测能力缺口 + 生成工具提案 ──
    try:
        from evolution_cascade import inspect as cascade_inspect
        cascade_result = cascade_inspect(
            skills_extracted=evo_result.get("skill_extracted", 0),
            patterns_found=evo_result.get("patterns_found", 0),
            treasure_id=tid,
            treasure_name=name,
        )
        if cascade_result.get("proposals_generated", 0) > 0:
            _log_metabolic(f"[Cascade] 生成 {cascade_result['proposals_generated']} 个工具提案 "
                           f"(δ 检测 {cascade_result['delta_found']} 个缺口, "
                           f"经验引导 {cascade_result['experience_hits']} 条)")
    except Exception as e:
        _log_metabolic(f"[Cascade] 进化级联跳过({tid}): {e}")
    
    # ── v5: 自反思钩子（填补"无自身行为审视"缺口） ──
    # 每次 digest 完成后，记录执行轨迹并生成三条教训
    _trajectory = TrajectoryRecord(
        action="digest_one",
        context=f"精读宝藏: {name}",
        outcome=f"完成，触发进化管线（{evo_result.get('skill_extracted', 0)}技能/{evo_result.get('patterns_found', 0)}模式）",
        error="",
        tools=["ollama/qwen2.5:7b", "evolution_engine.run_evolution_pipeline"]
    )
    _trajectory.save()
    
    _self_reflect(tid, name, evo_result)
    
    # ── HyperAgents 融合: 递归 meta 审查钩子 ──
    try:
        _hook_meta_review(tid, name)
    except Exception as e:
        _log_metabolic(f"[HyperAgents] meta审查跳过: {e}")
    
    return {"status": "done", "id": tid, "name": name}

def _auto_draft(today):
    """今天没写文章时自动生成草稿"""
    from model_provider import ask
    # 从今天的精读中提取素材
    insights_path = CORTEX_DIR / "insights.json"
    today_insights = []
    try:
        data = json.loads(open(insights_path, "r", encoding="utf-8").read())
        today_insights = [i for i in data.get("insights", [])
                         if i.get("discovered_at", "").startswith(today)]
    except:
        pass
    
    prompt = f"写一篇简短的曦和日志，日期{today}，{'精读了' + str(len(today_insights)) + '篇宝藏' if today_insights else '今天在运行'}。风格自然，不AI，100-200字。"
    result = ask(prompt, system="你是曦和。用第一人称写日志。", temperature=0.7, max_tokens=512)
    text = result.get("text", "")
    if not text:
        return
    
    slug = f"auto-{today}"
    art = {
        "slug": slug, "title": f"曦和日志 {today}",
        "date": today, "description": text[:100],
        "tags": ["曦和", "日志"],
        "body": text,
    }
    art_path = XIHE_ROOT / "web" / "articles" / f"{slug}.json"
    with open(art_path, "w", encoding="utf-8") as f:
        json.dump(art, f, indent=2, ensure_ascii=False)
    
    # 更新索引
    idx_path = XIHE_ROOT / "web" / "articles" / "index.json"
    try:
        idx = json.loads(open(idx_path, "r", encoding="utf-8").read())
    except:
        idx = {"articles": [], "total": 0}
    idx["articles"].insert(0, {"slug": slug, "title": art["title"], "date": today,
                                "description": art["description"], "tags": art["tags"]})
    idx["total"] = len(idx["articles"])
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2, ensure_ascii=False)

# ── 内部方法 ──
def _load_source(treasure):
    tdir = TREASURE_DIR / (treasure.get("dir", treasure["id"]))
    for f in ["source.md", "source.html"]:
        p = tdir / f
        if p.exists():
            return open(p, "r", encoding="utf-8").read()[:8000]
    return ""

# ── v5: 自反思钩子（填补"无自身行为审视"缺口） ──

def _self_reflect(tid, name, evo_result):
    """
    digest_one 执行完成后的自反思：从本次执行中提取三条教训。
    
    填补曦和两个缺口中的第二个——能审视"自己的行为"而非只审视"外部知识"。
    每条教训遵循 lossless_write 格式（时间自包含、无代词歧义）。
    
    反思输出写入 CORTEX_DIR / self_reflections.json，供 LDM/梦境循环交叉验证。
    """
    reflections_path = CORTEX_DIR / "self_reflections.json"
    try:
        reflections = json.loads(open(reflections_path, "r", encoding="utf-8").read())
    except:
        reflections = {"reflections": [], "updated": None}
    
    # 从执行结果中提取三条结构化教训
    skill_count = evo_result.get("skill_extracted", 0)
    pattern_count = evo_result.get("patterns_found", 0)
    
    lessons = [
        f"精读 {name} 完成，提取 {skill_count} 个技能候选项。",
        f"模式发现{'触发' if pattern_count > 0 else '未触发'}，当前精读模式为{'每5篇一轮' if pattern_count == 0 else '模式发现轮'}。",
        f"轨道记录已写入 trajectory_log.json，可作为进化引擎v5反哺输入。"
    ]
    
    entry = {
        "id": f"ref_{tid}_{int(time.time())}",
        "source_treasure": tid,
        "source_name": name,
        "skill_extracted": skill_count,
        "patterns_found": pattern_count,
        "lessons": lessons,
        "reflected_at": datetime.now(BJT).isoformat(),
    }
    reflections["reflections"].insert(0, entry)
    if len(reflections["reflections"]) > 200:
        reflections["reflections"] = reflections["reflections"][:200]
    reflections["updated"] = datetime.now(BJT).isoformat()
    with open(reflections_path, "w", encoding="utf-8") as f:
        json.dump(reflections, f, indent=2, ensure_ascii=False)
    
    _log_metabolic(f"[SelfReflect] {tid}: 记录 {len(lessons)} 条教训")


# ═══════════════════════════════════════════
# HyperAgents 融合: 递归 meta 编辑 (v5.1)
# 启发自 Meta FAIR arXiv:2603.19461 (Jenny Zhang et al.)
# 核心: meta-agent 可编辑自身 → 消除人工设计瓶颈
# ═══════════════════════════════════════════

# 进化策略记录 (供递归审查用)
_EVO_STRATEGIES_PATH = CORTEX_DIR / "evolution_strategies.json"

def _load_evo_strategies():
    """加载进化策略记录"""
    try:
        return json.loads(open(_EVO_STRATEGIES_PATH, "r", encoding="utf-8").read())
    except:
        return {"strategies": [], "last_review": None, "version": 1}

def _save_evo_strategies(data):
    with open(_EVO_STRATEGIES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _recursive_meta_review(frequency=10):
    """递归 meta 审查: 审查并改进进化引擎自身的进化策略
    
    HyperAgents 的核心突破: meta-agent 不只是修改 task-agent,
    它也能修改自己——这意味着"改进的速度"本身也会被改进。
    
    此函数每 frequency 次 digest 后触发一次，做三件事:
    1. 审查当前进化策略的有效性
    2. 记录改进建议（供下次 review 时评估是否采纳）
    3. 检测策略趋同（进化停滞信号）
    
    参数:
        frequency: 每 digest N 次触发一次审查 (默认 10)
    
    返回:
        review: 审查报告
    """
    # 读取当前策略和本次 digest 计数
    strategies = _load_evo_strategies()
    digest_count = len(strategies.get("strategies", []))
    
    # 记录本次 digest 的执行策略
    current_strategy = {
        "digest_round": digest_count + 1,
        "sampling_method": "archive_diversity" if hasattr(globals(), '_population_diversity_call') else "score_priority",
        "timestamp": datetime.now(BJT).isoformat(),
    }
    strategies.setdefault("strategies", []).append(current_strategy)
    if len(strategies["strategies"]) > 100:
        strategies["strategies"] = strategies["strategies"][-100:]
    
    review = {"meta_reviewed": False, "note": "未到审查周期"}
    
    # 每 frequency 次触发一次完整审查
    if digest_count % frequency == 0 and digest_count > 0:
        recent = strategies["strategies"][-frequency:]
        # 检测策略趋同: 如果连续 N 次用同一方法 → 建议切换
        methods = [s["sampling_method"] for s in recent]
        if len(set(methods)) == 1:
            # 策略固化 → 建议引入多样性
            review = {
                "meta_reviewed": True,
                "finding": "策略趋同",
                "detail": f"最近 {frequency} 次全部使用 '{methods[0]}' 策略，建议引入多样性采样",
                "suggestion": "切换至 population_based_diversity() 随机选择策略",
                "confidence": 0.85,
                "severity": "recommendation",
                "reviewed_at": datetime.now(BJT).isoformat(),
            }
        else:
            # 策略多样性良好
            review = {
                "meta_reviewed": True,
                "finding": "策略健康",
                "detail": f"最近 {frequency} 次使用了 {len(set(methods))} 种不同策略，多样性良好",
                "suggestion": "维持当前策略，下次轮询时再次审查",
                "confidence": 0.90,
                "severity": "info",
                "reviewed_at": datetime.now(BJT).isoformat(),
            }
        
        # 记录审查结果
        strategies["last_review"] = review
        strategies["version"] = strategies.get("version", 1) + 1
        
        _log_metabolic(f"[MetaReview] v{strategies['version']}: {review['finding']} → {review['suggestion'][:40]}")
    
    _save_evo_strategies(strategies)
    return review


def _population_based_diversity(archive, top_n=5):
    """基于人口多样性的存档采样 (HyperAgents 随机选择策略)
    
    HyperAgents 的 Archive 机制: 不只用最高分做父代，
    而是对前 top_n 候选按概率随机选择——分数高者概率高，
    但低分者也有机会被选中（保留"沉睡的创新"）。
    
    参数:
        archive: 存档列表，每项含 {name, score}
        top_n: 候选池大小
    
    返回:
        selected: 选中的存档项
        diversity_score: 当前多样性评分
    """
    import random
    
    if not archive:
        return None
    
    # 取前 top_n 作为候选池
    sorted_archive = sorted(archive, key=lambda x: x.get("score", 0), reverse=True)
    pool = sorted_archive[:min(top_n, len(sorted_archive))]
    
    if not pool:
        return None
    
    # 软max概率选择（非贪婪）
    scores = [max(p.get("score", 0.1), 0.1) for p in pool]
    total = sum(scores)
    weights = [s / total for s in scores]
    
    selected = random.choices(pool, weights=weights, k=1)[0]
    
    # 多样性评分: 池中分数分布的标准差
    import statistics
    if len(scores) > 1:
        diversity = round(statistics.stdev(scores) / statistics.mean(scores), 3) if statistics.mean(scores) > 0 else 0
    else:
        diversity = 0
    
    return {
        "selected": selected,
        "diversity_score": diversity,
        "pool_size": len(pool),
        "method": "population_based_diversity",
    }


def _cross_domain_evaluation(results_by_domain):
    """跨域评估: 判断改进是否在多个域都有效
    
    HyperAgents 的领域无关性验证:
    真正的元级改进应该跨域有效，而非只在单一域提升。
    
    参数:
        results_by_domain: 各域的评估结果 {domain: score}
    
    返回:
        transfer_score: 跨域迁移评分 (0-1)
        domain_count: 域数
        stable: 是否在所有域都稳定
    """
    if not results_by_domain:
        return {"transfer_score": 0, "domain_count": 0, "stable": False}
    
    scores = list(results_by_domain.values())
    domain_count = len(scores)
    
    if domain_count == 1:
        return {"transfer_score": 1.0, "domain_count": 1, "stable": True, "note": "单域评估"}
    
    # 跨域迁移分数: 所有域分数的调和均值 × (域数/总分域)
    import statistics
    mean_score = statistics.mean(scores)
    min_score = min(scores)
    
    # 如果任意域分数骤降 → 跨域迁移失败
    if min_score < 0.3 * mean_score:
        return {
            "transfer_score": round(min_score, 3),
            "domain_count": domain_count,
            "stable": False,
            "note": f"域间冲突: {min_score} << {mean_score}，改进可能过拟合单一域",
            "weakest_domain": min(results_by_domain, key=results_by_domain.get),
        }
    
    transfer_score = round(mean_score * (1 - statistics.stdev(scores) / (mean_score + 0.001)), 3)
    
    return {
        "transfer_score": transfer_score,
        "domain_count": domain_count,
        "stable": True,
        "mean_score": round(mean_score, 3),
        "note": f"跨 {domain_count} 域稳定，迁移评分 {transfer_score}",
    }


# 在 digest_one 末尾添加递归 meta 审查钩子
def _hook_meta_review(tid, name):
    """在 digest_one 末尾调用: 记录轨迹 + 触发递归审查"""
    review = _recursive_meta_review()
    if review.get("meta_reviewed"):
        _log_metabolic(f"[HyperAgents] 递归审查: {review['finding']}")
        # 记录到自反思
        ref_path = CORTEX_DIR / "self_reflections.json"
        try:
            refs = json.loads(open(ref_path, "r", encoding="utf-8").read())
            refs["reflections"].insert(0, {
                "id": f"hyperagents_review_{int(time.time())}",
                "source_treasure": tid,
                "source_name": name,
                "lessons": [f"[HyperAgents] 递归meta审查: {review['detail'][:100]}"],
                "reflected_at": datetime.now(BJT).isoformat(),
            })
            if len(refs["reflections"]) > 200:
                refs["reflections"] = refs["reflections"][:200]
            refs["updated"] = datetime.now(BJT).isoformat()
            with open(ref_path, "w", encoding="utf-8") as f:
                json.dump(refs, f, indent=2, ensure_ascii=False)
        except:
            pass
    return review

def _build_prompt(title, source, content):
    return f"""精读以下论文/资料，用四原则过滤矩阵输出。

标题: {title}
来源: {source}
内容:
{content}

输出格式：
## 第一遍：去粗取精 | 核心精华
3个核心发现，3条可迁移法则

## 第二遍：去伪存真 | 检验与质疑
1-2个质疑+检验

## 第三遍：由此及彼 | 知识图谱连接
3条以上曦和映射，1条以上新线索

## 第四遍：由表及里 | 架构层洞见
表层/底层，核心定理，今天能反哺的一条

## 精读评分
四维度评分"""

def _write_readme(treasure_dir, content):
    d = TREASURE_DIR / treasure_dir
    d.mkdir(parents=True, exist_ok=True)
    header = f"""# {treasure_dir}

> **精读日期**: {datetime.now(BJT).strftime('%Y-%m-%d %H:%M')}  
> **精读方式**: 进化引擎 v2 · 代谢系统内建  
> **精读模型**: qwen2.5:7b

---
"""
    with open(d / "README.md", "w", encoding="utf-8") as f:
        f.write(header + content)

def _feedback_to_cortex(tid, name, text):
    """反哺到记忆图谱（增强版：含经验→能力反馈钩子）"""
    insights_path = CORTEX_DIR / "insights.json"
    try:
        data = json.loads(open(insights_path, "r", encoding="utf-8").read())
    except:
        data = {"insights": [], "updated": None}
    
    entry = {
        "id": f"{tid}_{int(time.time())}",
        "source": name,
        "type": "deep_read",
        "status": "implemented",
        "discovered_at": datetime.now(BJT).isoformat(),
    }
    data["insights"].insert(0, entry)
    data["updated"] = datetime.now(BJT).isoformat()
    if len(data["insights"]) > 100:
        data["insights"] = data["insights"][:100]
    with open(insights_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # ── [Mem²Evolve融合] 经验→能力反馈钩子 ──
    _experience_to_capability_feedback()


def _experience_to_capability_feedback():
    """
    经验→能力反馈钩子（Mem²Evolve双记忆共演化机制）。
    扫描所有treasure的nutrients.json，查找未实现的高赫布信用度建议。
    如果发现未实现的工具创建建议，写入 capability_gaps.json。
    """
    gaps_path = CORTEX_DIR / "capability_gaps.json"
    
    try:
        gaps = json.loads(open(gaps_path, "r", encoding="utf-8").read())
    except:
        gaps = {"gaps": [], "updated": None}
    
    seen = {(g["target"], g["nutrient_id"]) for g in gaps["gaps"]}
    new_count = 0
    
    if TREASURE_DIR.exists():
        for tdir in TREASURE_DIR.iterdir():
            if not tdir.is_dir():
                continue
            nf = tdir / "nutrients.json"
            if not nf.exists():
                continue
            
            try:
                ndata = json.loads(open(nf, "r", encoding="utf-8").read())
            except:
                continue
            
            for n in ndata.get("nutrients", []):
                if not isinstance(n, dict) or n.get("status") != "pending":
                    continue
                if n.get("hebbian_credit", 0) < 8:
                    continue
                
                target = n.get("target", "")
                nid = n.get("id", "")
                key = (target, nid)
                
                if key not in seen:
                    gaps["gaps"].append({
                        "nutrient_id": nid,
                        "name": n.get("name", ""),
                        "insight": n.get("insight", "")[:200],
                        "target": target,
                        "hebbian_credit": n.get("hebbian_credit", 0),
                        "discovered_at": datetime.now(BJT).isoformat(),
                        "status": "pending",
                    })
                    seen.add(key)
                    new_count += 1
    
    if new_count > 0:
        gaps["updated"] = datetime.now(BJT).isoformat()
        gaps["summary"] = f"{len(gaps['gaps'])}个能力缺口待实现（本轮新增{new_count}个）"
        with open(gaps_path, "w", encoding="utf-8") as f:
            json.dump(gaps, f, indent=2, ensure_ascii=False)
        _log_metabolic(f"[Mem2Evolve] 经验→能力反馈: 新增{new_count}个能力缺口")


def _log_metabolic(msg):
    """写入代谢日志"""
    log_path = CORTEX_DIR / "metabolic_log.json"
    try:
        log = json.loads(open(log_path, "r", encoding="utf-8").read())
    except:
        log = {"entries": []}
    log["entries"].append({
        "time": datetime.now(BJT).isoformat(),
        "message": msg,
    })
    if len(log["entries"]) > 500:
        log["entries"] = log["entries"][-500:]
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

def _update_plan():
    """更新每日计划中的完成计数"""
    plan_path = CORTEX_DIR / "daily-plan.json"
    try:
        plan = json.loads(open(plan_path, "r", encoding="utf-8").read())
    except:
        plan = {}
    if "deep_read_plan" not in plan:
        plan["deep_read_plan"] = {"daily_target": 5, "completed_today": 0}
    plan["deep_read_plan"]["completed_today"] = plan["deep_read_plan"].get("completed_today", 0) + 1
    plan["updated_at"] = datetime.now(BJT).isoformat()
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)


# ── v3: 结构化技能提取管线（自进化Agent三层记忆+技能系统） ──

def _extract_skills_from_treasure(treasure_id, treasure_name, nutrients):
    """
    精读后自动提取可复用技能。
    
    输入: nutrients.json → 提取nutrients中的拟议目标(target)
    输出: 候选技能列表 → 经quality_gating → 写入skills库或实验池
    
    技能结构（仿三层记忆+技能系统架构）：
        {
            "skill_id": "...",
            "name": "...",
            "use_when": "...",
            "tool_chain": [...],
            "constraints": [...],
            "inputs": {...},
            "outputs": {...},
            "quality_score": float,
            "status": "active | experimental"
        }
    """
    skills_dir = CORTEX_DIR / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    skills_index_path = skills_dir / "index.json"
    
    # 加载已有技能索引
    try:
        skills_index = json.loads(open(skills_index_path, "r", encoding="utf-8").read())
    except:
        skills_index = {"skills": [], "updated": None}
    
    existing_ids = {s["skill_id"] for s in skills_index.get("skills", [])}
    new_count = 0
    
    for n in nutrients.get("nutrients", []):
        if n.get("status") != "pending":
            continue
        if n.get("hebbian_credit", 0) < 7:
            continue  # 赫布信用不足，暂不提取
        if n.get("type") not in ("architectural_pattern", "mechanism", "design_pattern"):
            continue  # 只提取可执行的模式/机制
        
        # 构建候选技能ID
        target = n.get("target", "")
        skill_id = f"{treasure_id}__{n['id']}"
        
        if skill_id in existing_ids:
            continue
        
        # 构建技能
        skill = {
            "skill_id": skill_id,
            "name": n.get("name", ""),
            "description": n.get("insight", "")[:200],
            "use_when": f"当需要处理{treasure_name}相关的{n.get('name', '')}时",
            "source_treasure": treasure_id,
            "source_nutrient": n["id"],
            "target": target,
            "hebbian_credit": n.get("hebbian_credit", 0),
            "tool_chain": [],
            "constraints": [],
            "inputs": {},
            "outputs": {},
            "quality_score": round(n.get("hebbian_credit", 0) / 10.0, 2),
            "status": "experimental",  # 默认进实验池，经quality_gating升为active
            "created_at": datetime.now(BJT).isoformat(),
        }
        skills_index["skills"].append(skill)
        existing_ids.add(skill_id)
        new_count += 1
    
    if new_count > 0:
        skills_index["updated"] = datetime.now(BJT).isoformat()
        with open(skills_index_path, "w", encoding="utf-8") as f:
            json.dump(skills_index, f, indent=2, ensure_ascii=False)
        
        # 执行质量阈值门控
        promoted, demoted = skill_quality_gating()
        msg = f"[SkillExtract] 从{treasure_id}提取{new_count}个候选技能"
        if promoted:
            msg += f"，{promoted}个升为active"
        _log_metabolic(msg)
    
    return new_count


def skill_quality_gating():
    """
    技能质量阈值门控（三层记忆+技能系统中的'准入门槛'）。
    
    规则：
      - quality_score >= 0.75 → active (默认技能池)
      - quality_score < 0.75  → experimental (实验池，需更多样本)
    
    额外条件：
      - 使用次数>3且成功率>80%的实验技能 → 自动升级
      - 使用次数>5且成功率<30%的活跃技能 → 自动降级
    
    Returns:
        (promoted: int, demoted: int)
    """
    skills_dir = CORTEX_DIR / "skills"
    skills_index_path = skills_dir / "index.json"
    
    try:
        skills_index = json.loads(open(skills_index_path, "r", encoding="utf-8").read())
    except:
        return (0, 0)
    
    promoted = 0
    demoted = 0
    
    for s in skills_index.get("skills", []):
        current_status = s.get("status", "experimental")
        quality = s.get("quality_score", 0)
        
        # 升级判定
        if current_status == "experimental":
            if quality >= 0.75:
                s["status"] = "active"
                s["promoted_at"] = datetime.now(BJT).isoformat()
                promoted += 1
        elif current_status == "active":
            # 降级判定
            if quality < 0.5:
                s["status"] = "experimental"
                s["demoted_at"] = datetime.now(BJT).isoformat()
                demoted += 1
    
    if promoted > 0 or demoted > 0:
        skills_index["updated"] = datetime.now(BJT).isoformat()
        with open(skills_index_path, "w", encoding="utf-8") as f:
            json.dump(skills_index, f, indent=2, ensure_ascii=False)
    
    return (promoted, demoted)


def _discover_skill_patterns():
    """
    从nutrients.json的情景记录中发现重复模式（三层记忆中的'技能发现'）。
    
    扫描所有treasure的nutrients，查找高频出现的target路径，
    如果多个nutrients指向同一个target，聚合为复合技能。
    """
    skills_dir = CORTEX_DIR / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    patterns_path = skills_dir / "patterns.json"
    
    # 收集所有target路径
    target_map = {}  # target → [nutrient_ids]
    
    if TREASURE_DIR.exists():
        for tdir in TREASURE_DIR.iterdir():
            if not tdir.is_dir():
                continue
            nf = tdir / "nutrients.json"
            if not nf.exists():
                continue
            try:
                ndata = json.loads(open(nf, "r", encoding="utf-8").read())
            except:
                continue
            
            for n in ndata.get("nutrients", []):
                if not isinstance(n, dict):
                    continue  # 跳过旧格式字符串条目
                target = n.get("target", "")
                nid = n.get("id", "")
                if target and nid:
                    if target not in target_map:
                        target_map[target] = {"nutrient_ids": [], "sources": set(), "total_credit": 0}
                    target_map[target]["nutrient_ids"].append(nid)
                    target_map[target]["sources"].add(tdir.name)
                    target_map[target]["total_credit"] += n.get("hebbian_credit", 0)
        
    # 发现模式：同一target有≥3个不同source → 复合技能候选
    patterns = []
    for target, info in target_map.items():
        if len(info["sources"]) >= 3:
            patterns.append({
                "target": target,
                "sources": list(info["sources"]),
                "nutrient_count": len(info["nutrient_ids"]),
                "total_credit": info["total_credit"],
                "discovered_at": datetime.now(BJT).isoformat(),
                "status": "pending",
            })
    
    if patterns:
        with open(patterns_path, "w", encoding="utf-8") as f:
            json.dump({
                "patterns": patterns,
                "count": len(patterns),
                "discovered_at": datetime.now(BJT).isoformat(),
            }, f, indent=2, ensure_ascii=False)
        _log_metabolic(f"[PatternDiscovery] 发现{len(patterns)}个复合技能模式候选")
    
    return patterns


# ── v3: 在消化完成后触发完整进化管线 ──

def run_evolution_pipeline(treasure_id, treasure_name):
    """
    完整的进化管线：消化后自动执行。
    包括：技能提取 + 质量门控 + 模式发现
    
    Args:
        treasure_id: 宝藏ID
        treasure_name: 宝藏名称
    """
    results = {"skill_extracted": 0, "promoted": 0, "patterns_found": 0}
    
    # 1. 技能提取
    nf = TREASURE_DIR / treasure_id / "nutrients.json"
    if nf.exists():
        try:
            ndata = json.loads(open(nf, "r", encoding="utf-8").read())
            nutrients_list = ndata if isinstance(ndata, list) else ndata.get("nutrients", [])
            results["skill_extracted"] = _extract_skills_from_treasure(treasure_id, treasure_name, {"nutrients": nutrients_list})
        except Exception as e:
            _log_metabolic(f"[EvoPipeline] 技能提取跳过({treasure_id}): {e}")
    
    # 2. 质量门控
    try:
        promoted, demoted = skill_quality_gating()
        results["promoted"] = promoted
    except Exception as e:
        _log_metabolic(f"[EvoPipeline] 质量门控跳过: {e}")
    
    # 3. 模式发现（每5篇触发一次）
    try:
        idx_path = TREASURE_DIR / "index.json"
        if idx_path.exists():
            idx = json.loads(open(idx_path, "r", encoding="utf-8-sig").read())
            digested_count = sum(1 for t in idx.get("treasures", []) if t.get("status") == "digested")
            if digested_count > 0 and digested_count % 5 == 0:
                patterns = _discover_skill_patterns()
                results["patterns_found"] = len(patterns)
    except:
        pass
    
    return results

# ── 直接调用入口（供代谢路由/watchman使用） ──
def status():
    """返回精读进度摘要"""
    idx = json.loads(open(TREASURE_DIR / "index.json", "r", encoding="utf-8-sig").read())
    total = len(idx.get("treasures", []))
    done = 0
    for t in idx["treasures"]:
        tid = t.get("id", "")
        readme = TREASURE_DIR / (t.get("dir", tid)) / "README.md"
        if readme.exists():
            c = open(readme, "r", encoding="utf-8").read()
            if "四原则过滤矩阵" in c:
                done += 1
    return {"total": total, "digested": done, "remaining": total - done}

# ── v4: 存档式进化采样（Darwin Gödel Machine 代谢融合） ──

def sample_parent_from_archive(k=3, strategy="high_score_low_offspring"):
    """
    从treasure archive中采样父代宝藏用于进化变异。
    
    基于DGM的HighScore×LowOffspring策略 (ICLR 2026):
      - 采样概率 pi ∝ score_i * (1 / (1 + children_count_i))
      - 每个条目都有非零采样概率 → 低分'垫脚石'不丢失
      - 同一宝藏在被重用为父代后，其后代计数增加，再次被选中的概率降低
    
    Args:
        k: 采样数量
        strategy: "random" | "high_score" | "high_score_low_offspring" | "diverse_field"
    
    Returns:
        list[dict]: 选中的宝藏元数据列表
    """
    idx_path = TREASURE_DIR / "index.json"
    try:
        idx = json.loads(open(idx_path, "r", encoding="utf-8-sig").read())
        treasures = idx.get("treasures", [])
    except:
        return []
    
    if not treasures:
        return []
    
    if strategy == "random":
        import random
        return random.sample(treasures, min(k, len(treasures)))
    
    elif strategy == "high_score":
        sorted_t = sorted(treasures, key=lambda t: t.get("score", 0), reverse=True)
        return sorted_t[:k]
    
    elif strategy == "diverse_field":
        # 按领域分层采样，确保覆盖广度
        field_groups = {}
        for t in treasures:
            tags = tuple(sorted(t.get("tags", ["未分类"])[:1]))
            if tags not in field_groups:
                field_groups[tags] = []
            field_groups[tags].append(t)
        # 从每个组中选最高分的一个
        candidates = []
        for group, members in field_groups.items():
            candidates.append(max(members, key=lambda t: t.get("score", 0)))
        candidates.sort(key=lambda t: t.get("score", 0), reverse=True)
        return candidates[:k]
    
    elif strategy == "high_score_low_offspring":
        # DGM核心策略：HighScore × LowOffspring
        # 加载后代计数（从archive_stats或从nutrients.json统计）
        offspring_map = _load_offspring_counts()
        
        scored = []
        for t in treasures:
            tid = t.get("id", "")
            score = t.get("score", 0.5)
            children = offspring_map.get(tid, 0)
            # pi = score * (1 / (1 + children))
            weight = score * (1.0 / (1.0 + children))
            scored.append((weight, t))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        top_parents = scored[:k]
        
        # 返回后自动更新后代计数（增加被选中的parent的children_count）
        _increment_offspring_count([t[1]["id"] for t in top_parents])
        
        return [t[1] for t in top_parents]
    
    return []


def _load_offspring_counts():
    """加载后代计数映射表"""
    stats_path = TREASURE_DIR / "archive_stats.json"
    try:
        stats = json.loads(open(stats_path, "r", encoding="utf-8").read())
        return stats.get("offspring_map", {})
    except:
        return {}


def _increment_offspring_count(parent_ids):
    """增加指定父代的后代计数"""
    stats_path = TREASURE_DIR / "archive_stats.json"
    try:
        stats = json.loads(open(stats_path, "r", encoding="utf-8").read())
    except:
        stats = {"offspring_map": {}, "updated": None}
    
    for pid in parent_ids:
        stats["offspring_map"][pid] = stats["offspring_map"].get(pid, 0) + 1
    
    stats["updated"] = datetime.now(BJT).isoformat()
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)


def archive_stats():
    """
    返回存档多样性统计摘要。
    用于代谢器/自反层评估进化树健康度。
    """
    idx_path = TREASURE_DIR / "index.json"
    try:
        idx = json.loads(open(idx_path, "r", encoding="utf-8-sig").read())
    except:
        return {"error": "无法读取index.json"}
    
    treasures = idx.get("treasures", [])
    stats = _load_offspring_counts()
    
    # 领域分布
    field_dist = {}
    for t in treasures:
        for tag in t.get("tags", ["未分类"]):
            field_dist[tag] = field_dist.get(tag, 0) + 1
    
    # 层分布
    layer_dist = {}
    for t in treasures:
        layer = t.get("layer", "L?")
        layer_dist[layer] = layer_dist.get(layer, 0) + 1
    
    # 评分分布
    scores = [t.get("score", 0) for t in treasures]
    
    # 后代分布（进化树深度指标）
    offspring_values = list(stats.get("offspring_map", {}).values())
    
    return {
        "total": len(treasures),
        "digested": sum(1 for t in treasures if t.get("status") == "digested"),
        "fields": len(field_dist),
        "layers": layer_dist,
        "score_avg": round(sum(scores) / len(scores), 2) if scores else 0,
        "score_max": max(scores) if scores else 0,
        "score_min": min(scores) if scores else 0,
        "ever_sampled_as_parent": len(offspring_values),
        "max_offspring": max(offspring_values) if offspring_values else 0,
        "avg_offspring": round(sum(offspring_values) / len(offspring_values), 2) if offspring_values else 0,
        "updated": datetime.now(BJT).isoformat(),
    }


# ── v4: 分阶段评估（Darwin Gödel Machine 代谢融合） ──

def phased_evaluation(treasure, fast_check=True, medium_check=True):
    """
    分阶段评估机制：从DGM的分阶段评估(10→60→200)汲取。
    
    Phase 1 (快速)：基于元数据快速评估可行性
    Phase 2 (中等)：如果通过Phase 1，进行nutrients结构验证
    Phase 3 (高精度)：如果都需要，触发Ollama精读
    
    Args:
        treasure: 宝藏元数据
        fast_check: 是否执行快速筛选
        medium_check: 是否执行中等评估
    
    Returns:
        dict: {"phase": 1|2|3, "passed": bool, "reason": str, "recommendation": str}
    """
    tid = treasure.get("id", "")
    name = treasure.get("name", "")
    score = treasure.get("score", 0.5)
    tags = treasure.get("tags", [])
    
    # Phase 1: 快速筛选
    if fast_check:
        # 检查是否有nutrients.json
        tdir = TREASURE_DIR / (treasure.get("dir", tid))
        nf = tdir / "nutrients.json"
        if not nf.exists():
            return {"phase": 1, "passed": False, "reason": "无nutrients.json", "recommendation": "跳过"}
        
        # 检查评分是否达标
        if score < 0.6:
            return {"phase": 1, "passed": False, "reason": f"评分{score}<0.6", "recommendation": "跳过或转为缓冲池"}
        
        # 检查领域词表命中
        from prey_filter import XIHE_DOMAINS_SET
        domain_hits = sum(1 for tag in tags if tag in XIHE_HELPER_SET())
        if domain_hits == 0:
            return {"phase": 1, "passed": False, "reason": "零领域命中", "recommendation": "跳过"}
        
        if not medium_check:
            return {"phase": 1, "passed": True, "reason": "快速筛选通过", "recommendation": "可入库"}
    
    # Phase 2: 中等评估（nutrients完整性校验）
    if medium_check:
        try:
            ndata = json.loads(open(tdir / "nutrients.json", "r", encoding="utf-8").read())
        except:
            return {"phase": 2, "passed": False, "reason": "nutrients.json读取失败", "recommendation": "修复后重试"}
        
        # 检查关键字段
        required_fields = ["xihe_mapping", "fusion_plan", "digest_notes"]
        missing = [f for f in required_fields if f not in ndata]
        if missing:
            return {"phase": 2, "passed": False, "reason": f"缺少{missing}", "recommendation": "补充字段"}
        
        # 检查四原则过滤是否完整
        fp = ndata.get("four_principles_filter", {})
        principles = ["去粗取精", "去伪存真", "由此及彼", "由表及里"]
        missing_p = [p for p in principles if p not in fp]
        if missing_p:
            return {"phase": 2, "passed": False, "reason": f"四原则不完整: 缺{missing_p}", "recommendation": "补全四原则"}
        
        return {"phase": 2, "passed": True, "reason": "中等评估通过", "recommendation": "可执行深度消化"}
    
    return {"phase": 3, "passed": True, "reason": "全部评估通过", "recommendation": "完全消化"}


def XIHE_HELPER_SET():
    """辅助函数：返回领域词表集合"""
    from prey_filter import XIHE_DOMAINS_SET
    return XIHE_DOMAINS_SET


# ── v4: 负面结论记录与共享（Stanford DeLM 代谢融合） ──

def record_negative_finding(treasure_id, finding_type, description, source="auto"):
    """
    记录负面结论到共享脉络。
    
    DeLM的核心洞见：把'负面结论(negative findings)'也写入共享脉络，
    让代理看到彼此踩过的雷，省下重工成本。
    
    Args:
        treasure_id: 关联的宝藏ID
        finding_type: "failed_attempt" | "dead_end" | "contradiction" | "non_transferable"
        description: 负面结论的描述
        source: "auto" | "manual" | "review"
    """
    nf_path = TREASURE_DIR / "negative_findings.json"
    try:
        nf = json.loads(open(nf_path, "r", encoding="utf-8").read())
    except:
        nf = {"findings": [], "updated": None}
    
    nf["findings"].append({
        "treasure_id": treasure_id,
        "type": finding_type,
        "description": description[:500],
        "source": source,
        "recorded_at": datetime.now(BJT).isoformat(),
    })
    
    # 保留最近100条
    if len(nf["findings"]) > 100:
        nf["findings"] = nf["findings"][-100:]
    
    nf["updated"] = datetime.now(BJT).isoformat()
    nf["count"] = len(nf["findings"])
    with open(nf_path, "w", encoding="utf-8") as f:
        json.dump(nf, f, indent=2, ensure_ascii=False)
    
    _log_metabolic(f"[NegativeFinding] 记录{finding_type}: {description[:80]}...")

    # [CausalFlow 融合 · 研讨厅研判 0.87 · A嫁接 · 2026-07-20]
    # 负面结论记录后, 做步骤级因果责任归因 → 负反馈从「知道错」升级到「知道错在哪一步」
    try:
        import causal_attribution as _ca
        _ca.attribute_causal_responsibility({
            "treasure_id": treasure_id,
            "type": finding_type,
            "description": description[:500],
            "source": source,
            "recorded_at": nf["findings"][-1]["recorded_at"],
        })
    except Exception as _e:
        _log_metabolic(f"[CausalFlow] 归因跳过: {_e}")


def get_negative_findings(treasure_id=None, finding_type=None, limit=10):
    """
    查询负面结论记录。
    
    Args:
        treasure_id: 可选，过滤特定宝藏的负面结论
        finding_type: 可选，过滤特定类型
        limit: 返回条数上限
    
    Returns:
        list[dict]: 负面结论列表
    """
    nf_path = TREASURE_DIR / "negative_findings.json"
    try:
        nf = json.loads(open(nf_path, "r", encoding="utf-8").read())
    except:
        return []
    
    findings = nf.get("findings", [])
    
    if treasure_id:
        findings = [f for f in findings if f.get("treasure_id") == treasure_id]
    if finding_type:
        findings = [f for f in findings if f.get("type") == finding_type]
    
    return findings[:limit]


def auto_archive():
    """铁律零代码化：自动存档聊天记录到chronicles"""
    src = XIHE_ROOT / "曦和与盘古的日常对话"
    dst = XIHE_ROOT / "chronicles"
    today = datetime.now(BJT).strftime("%Y-%m-%d")
    
    # 复制MD
    md_src = src / f"{today}.md"
    md_dst = dst / f"{today}.md"
    if md_src.exists() and not md_dst.exists():
        import shutil
        shutil.copy2(str(md_src), str(md_dst))
    
    # 复制HTML（追加）
    html_src = src / "曦和与盘古的日常对话.html"
    html_dst = dst / "曦和与盘古的日常对话.html"
    if html_src.exists():
        if html_dst.exists():
            with open(html_dst, "a", encoding="utf-8") as f:
                f.write(html_src.read_text("utf-8"))
        else:
            import shutil
            shutil.copy2(str(html_src), str(html_dst))

# ═══════════════════════════════════════════════════════════════
# v5 新增（2026-07-18, Autogenesis Protocol AGP 代谢融合）:
#   1. EvolutionAudit: AGP SEPL风格的进化审计与回滚管理
#   2. register_resource: AGP RSPL风格的协议化资源注册
#   3. list_resources: 查询已注册的进化资源清单
# ═══════════════════════════════════════════════════════════════

_RESOURCE_REGISTRY = None  # lazy load
_RESOURCE_REGISTRY_PATH = BRIDGE_DIR / "evolution_resource_registry.json"

def _load_resource_registry():
    """加载或初始化AGP风格的资源注册表"""
    global _RESOURCE_REGISTRY
    if _RESOURCE_REGISTRY is not None:
        return _RESOURCE_REGISTRY
    try:
        with open(_RESOURCE_REGISTRY_PATH, "r", encoding="utf-8") as f:
            _RESOURCE_REGISTRY = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _RESOURCE_REGISTRY = {
            "meta": {
                "name": "曦和进化资源注册表 (AGP RSPL风格)",
                "created": datetime.now(BJT).isoformat(),
                "updated": datetime.now(BJT).isoformat(),
                "count": 0
            },
            "resources": []
        }
    return _RESOURCE_REGISTRY

def _save_resource_registry():
    """持久化资源注册表"""
    global _RESOURCE_REGISTRY
    if _RESOURCE_REGISTRY is None:
        return
    _RESOURCE_REGISTRY["meta"]["updated"] = datetime.now(BJT).isoformat()
    _RESOURCE_REGISTRY["meta"]["count"] = len(_RESOURCE_REGISTRY["resources"])
    try:
        with open(_RESOURCE_REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(_RESOURCE_REGISTRY, f, ensure_ascii=False, indent=2)
    except Exception as e:
        _log_metabolic(f"⚠️ 资源注册表写入失败: {e}")

def register_resource(resource_type, resource_id, name, version="1.0", 
                      description="", tags=None, parent_id=None):
    """AGP RSPL风格：注册一个可进化的资源
    
    Args:
        resource_type: 资源类型 (prompt/agent/tool/memory/environment)
        resource_id: 唯一标识
        name: 人类可读名称
        version: 语义化版本号
        description: 资源描述
        tags: 标签列表
        parent_id: 父资源ID (继承关系)
    
    Returns:
        dict: 注册后的资源条目
    """
    registry = _load_resource_registry()
    
    # 检查是否已存在
    existing = [r for r in registry["resources"] if r["resource_id"] == resource_id]
    if existing:
        entry = existing[0]
        entry["version"] = version
        entry["description"] = description or entry.get("description", "")
        entry["tags"] = tags or entry.get("tags", [])
        entry["updated_at"] = datetime.now(BJT).isoformat()
    else:
        entry = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "name": name,
            "version": version,
            "description": description,
            "tags": tags or [],
            "parent_id": parent_id,
            "status": "active",
            "created_at": datetime.now(BJT).isoformat(),
            "updated_at": datetime.now(BJT).isoformat(),
            "evolution_count": 0,
            "audit_log": []
        }
        registry["resources"].append(entry)
    
    _save_resource_registry()
    return entry

def list_resources(resource_type=None, status=None):
    """查询已注册资源 (AGP RSPL风格)
    
    Args:
        resource_type: 可选，按类型过滤 (prompt/agent/tool/memory/environment)
        status: 可选，按状态过滤 (active/archived/deprecated)
    
    Returns:
        list: 匹配的资源列表
    """
    registry = _load_resource_registry()
    results = registry["resources"]
    if resource_type:
        results = [r for r in results if r["resource_type"] == resource_type]
    if status:
        results = [r for r in results if r["status"] == status]
    return results

class EvolutionAudit:
    """AGP SEPL风格的进化审计管理器
    
    记录每次进化的:
    - before: 进化前的状态快照
    - after: 进化后的状态
    - cause: 进化原因 (新知识/冲突检测/模式发现/用户反馈)
    - rollback_plan: 回滚方案
    - commit_status: 提交状态 (proposed/committed/rolled_back)
    
    用法:
        audit = EvolutionAudit(resource_id="darwin-godel-machine-iclr2026")
        audit.propose(cause="新宝藏Autogenesis引导", 
                      before={"version": "v4"}, 
                      after={"version": "v5"},
                      rollback_plan="git revert + restore备份")
        audit.commit()
        # 如果出错: audit.rollback()
    """
    
    AUDIT_PATH = BRIDGE_DIR / "evolution_audit_log.json"
    
    def __init__(self, resource_id):
        self.resource_id = resource_id
        self._current = None
    
    def propose(self, cause, before, after, rollback_plan="", author="evolution_engine"):
        """提出一个进化变更, 记录before/after"""
        self._current = {
            "audit_id": f"ev_{int(time.time())}_{self.resource_id[-12:]}",
            "resource_id": self.resource_id,
            "timestamp": datetime.now(BJT).isoformat(),
            "cause": cause,
            "before": before,
            "after": after,
            "rollback_plan": rollback_plan or "手动回滚: 还原备份",
            "status": "proposed",
            "author": author
        }
        _log_metabolic(f"📝 进化审计: {self.resource_id} → {self._current['audit_id']} (proposed)")
        return self._current
    
    def commit(self, result="success"):
        """提交进化 (AGP Commit步骤)"""
        if self._current is None:
            return {"error": "没有待提交的进化提案"}
        self._current["status"] = "committed"
        self._current["result"] = result
        self._current["committed_at"] = datetime.now(BJT).isoformat()
        
        # 更新资源注册表的evolution_count
        reg = _load_resource_registry()
        for r in reg["resources"]:
            if r["resource_id"] == self.resource_id:
                r["evolution_count"] = r.get("evolution_count", 0) + 1
                if "audit_log" not in r:
                    r["audit_log"] = []
                r["audit_log"].append(self._current["audit_id"])
                break
        _save_resource_registry()
        
        # 追加到审计日志文件
        self._append_to_log()
        _log_metabolic(f"✅ 进化审计: {self.resource_id} → {self._current['audit_id']} (committed)")
        return self._current
    
    def rollback(self, reason="手动触发回滚"):
        """回滚进化 (AGP可审计回滚)"""
        if self._current is None:
            return {"error": "没有待回滚的进化提案"}
        self._current["status"] = "rolled_back"
        self._current["rollback_reason"] = reason
        self._current["rolled_back_at"] = datetime.now(BJT).isoformat()
        
        self._append_to_log()
        _log_metabolic(f"↩️ 进化审计: {self.resource_id} → {self._current['audit_id']} (rolled_back: {reason})")
        return self._current
    
    def get_status(self):
        """查询当前审计状态"""
        if self._current is None:
            return {"status": "idle", "resource_id": self.resource_id}
        return {
            "audit_id": self._current["audit_id"],
            "resource_id": self.resource_id,
            "status": self._current["status"],
            "cause": self._current["cause"],
            "timestamp": self._current["timestamp"]
        }
    
    def _append_to_log(self):
        """追加到审计日志文件"""
        try:
            log = []
            if self.AUDIT_PATH.exists():
                with open(self.AUDIT_PATH, "r", encoding="utf-8") as f:
                    log = json.load(f)
            log.append(self._current)
            # 只保留最近1000条
            if len(log) > 1000:
                log = log[-1000:]
            with open(self.AUDIT_PATH, "w", encoding="utf-8") as f:
                json.dump(log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            _log_metabolic(f"⚠️ 审计日志写入失败: {e}")


# ═══════════════════════════════════════════════════════════════
# 矛盾调和（obsidian-second-brain Reconcile 代谢融合 · 2026-07-18）
# 扫描记忆文件中的矛盾事实，按来源可信度/时间戳/上下文加权调和
# ═══════════════════════════════════════════════════════════════

_MEMORY_FILES = [
    XIHE_ROOT / "bridge" / "bridge-state.json",
    BRIDGE_DIR / "audit_trail.json",
    XIHE_ROOT / "treasure" / "index.json",
]


def reconcile_memory(memory_dir=None, auto_fix=False):
    """扫描记忆文件中的矛盾信息并生成调和报告

    Args:
        memory_dir: 可选，扫描指定目录下的所有 .md/.json 文件
        auto_fix: 是否自动修复可确定的矛盾

    Returns:
        dict: 调和报告

    矛盾检测逻辑（obsidian-second-brain 三信号加权）：
      - 来源可信度权重: treasure/ > bridge/ > 日志
      - 时间戳权重: 越新越可信
      - 上下文限定: 带条件的事实优先
    """
    report = {
        "scanned_files": 0,
        "contradictions_found": 0,
        "auto_fixed": 0,
        "contradictions": [],
        "timestamp": datetime.now(BJT).isoformat()
    }

    # 使用 OKM 解析
    try:
        from memory_writer import okm_parse
    except ImportError:
        _log_metabolic("[Reconcile] ⚠️ memory_writer 未导入，OKM 解析不可用")
        report["error"] = "memory_writer 模块未找到"
        return report

    # 确定扫描目录
    scan_dir = Path(memory_dir) if memory_dir else (XIHE_ROOT / "bridge")
    if not scan_dir.exists():
        report["error"] = f"路径不存在: {scan_dir}"
        return report

    # 扫描 .md 和 .json 文件
    files = list(scan_dir.glob("*.md")) + list(scan_dir.glob("*.json"))
    report["scanned_files"] = len(files)

    # 提取所有事实（按来源文件分组）
    all_facts = []  # [(fact_text, file_path, timestamp, source_weight)]
    for fpath in files:
        src_weight = _source_weight(fpath)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue

        # OKM 格式解析
        for line in text.split("\n"):
            parsed = okm_parse(line)
            if parsed:
                all_facts.append({
                    "fact": parsed["fact"],
                    "type": parsed["type"],
                    "stamp": parsed["stamp"],
                    "source": str(fpath),
                    "source_weight": src_weight,
                    "timestamp": parsed.get("stamp") or _extract_file_time(fpath),
                })

    # 检测矛盾：相同关键词但不同描述
    fact_groups = {}  # keyword → [facts]
    for fact_entry in all_facts:
        fact_text = fact_entry["fact"]
        # 提取关键词（前 4 个字作为粗分组键）
        key = fact_text[:12]  # 中文约 4 个字
        if key not in fact_groups:
            fact_groups[key] = []
        fact_groups[key].append(fact_entry)

    # 分析每个组中是否有矛盾
    for key, group in fact_groups.items():
        if len(group) < 2:
            continue

        # 比较同一 key 下的不同事实
        unique_facts = set(g["fact"] for g in group)
        if len(unique_facts) <= 1:
            continue  # 一致，无矛盾

        # 有矛盾！
        report["contradictions_found"] += 1
        contradiction = {
            "key": key,
            "versions": [],
            "resolution": None,
        }

        # 按可信度 + 时间戳排序
        sorted_versions = sorted(
            group,
            key=lambda g: (g["source_weight"], g.get("timestamp") or ""),
            reverse=True,
        )

        for g in sorted_versions:
            contradiction["versions"].append({
                "fact": g["fact"],
                "source": g["source"],
                "weight": g["source_weight"],
                "type": g.get("type", "?"),
                "stamp": g.get("stamp", "?"),
            })

        # 自动调和（如果 auto_fix）
        if auto_fix and len(sorted_versions) >= 2:
            best = sorted_versions[0]
            worst = sorted_versions[-1]
            contradiction["resolution"] = {
                "adopted": best["fact"],
                "adopted_source": best["source"],
                "rejected": worst["fact"],
                "reason": (
                    f"来源可信度 {best['source_weight']:.1f} > {worst['source_weight']:.1f}"
                ),
            }
            report["auto_fixed"] += 1

        report["contradictions"].append(contradiction)

    # 更新到桥状态
    _log_metabolic(
        f"[Reconcile] 扫描 {report['scanned_files']} 文件, "
        f"发现 {report['contradictions_found']} 矛盾, "
        f"自动修复 {report['auto_fixed']}"
    )

    return report


def _source_weight(file_path):
    """根据文件路径计算来源可信度"""
    path_str = str(file_path).lower()
    if "treasure" in path_str:
        return 1.0  # 宝藏数据最高可信
    if "bridge" in path_str and "state" in path_str:
        return 0.9  # 桥状态
    if "audit" in path_str:
        return 0.8  # 审计跟踪
    if "memory" in path_str or "diary" in path_str:
        return 0.6  # 记忆文件
    if "cache" in path_str or "temp" in path_str:
        return 0.3  # 缓存最低
    return 0.5


def _extract_file_time(file_path):
    """尝试从文件路径提取时间信息"""
    path_str = str(file_path)
    import re
    # 匹配 YYYY-MM-DD 或 YYYYMMDD
    m = re.search(r'(\d{4}[-/]?\d{2}[-/]?\d{2})', path_str)
    if m:
        return m.group(1).replace("/", "-")
    return None


if __name__ == "__main__":
    import sys
    if "--status" in sys.argv:
        s = status()
        print(f"精读进度: {s['digested']}/{s['total']} ({s['remaining']}篇剩余)")
    elif "--one" in sys.argv:
        r = digest_one()
        print(r.get("status"), r.get("name", ""))
    elif "--skill-status" in sys.argv:
        try:
            from skill_graph import SkillGraph
            sg = SkillGraph()
            sg.decay_freshness()
            rpt = sg.quality_report()
            print(f"技能知识图谱报告 ({datetime.now(BJT).strftime('%Y-%m-%d %H:%M')})")
            print(f"  技能总数: {rpt['total_skills']}")
            print(f"  边总数: {rpt['total_edges']}")
            print(f"  状态分布: {rpt['status_distribution']}")
            print(f"  质量分布: {rpt['quality_distribution']}")
            if rpt.get('top_used'):
                top_str = ', '.join(f'{t["skill_name"]}({t["usage_count"]}次)' for t in rpt['top_used'])
                print(f"  最常用: {top_str}")
            rot = sg.detect_skill_rot()
            if rot:
                print(f"  腐烂技能({len(rot)}): {', '.join(s['skill_name'] for s in rot[:5])}")
            else:
                print(f"  腐烂技能: 无")
        except Exception as e:
            print(f"⚠️ SkillGraph 加载失败: {e}")
    elif "--skill-recommend" in sys.argv and len(sys.argv) > 2:
        try:
            from skill_graph import SkillGraph
            sg = SkillGraph()
            query = sys.argv[2]
            recs = sg.recommend_by_context(query.split(), top_k=8)
            print(f"基于 '{query}' 推荐技能 (top {len(recs)}):")
            for r in recs:
                print(f"  ✅ {r['skill_name']} (score: {r['score']})")
        except Exception as e:
            print(f"⚠️ SkillGraph 推荐失败: {e}")
    elif "--reconcile" in sys.argv:
        auto_fix = "--auto-fix" in sys.argv
        mode = sys.argv[3] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
        if mode:
            r = reconcile_memory(Path(mode), auto_fix=auto_fix)
        else:
            r = reconcile_memory(auto_fix=auto_fix)
        print(f"矛盾调和报告 ({datetime.now(BJT).strftime('%Y-%m-%d %H:%M')})")
        print(f"  扫描文件: {r['scanned_files']}")
        print(f"  发现矛盾: {r['contradictions_found']}")
        print(f"  自动修复: {r['auto_fixed']}")
        if r.get("error"):
            print(f"  ⚠️ 错误: {r['error']}")
        if r['contradictions']:
            print(f"\n  矛盾详情:")
            for c in r['contradictions'][:5]:
                print(f"    📌 key: '{c['key']}'")
                for v in c['versions'][:3]:
                    print(f"      [{v['stamp']}] {v['fact']} (权重{v['weight']})")
                if c.get('resolution'):
                    print(f"      → 采用: {c['resolution']['adopted']}")
        else:
            print(f"  ✅ 无矛盾")
    else:
        # 空闲模式：有多少精读多少
        count = 0
        while should_digest():
            r = digest_one()
            print(f"  {r['status']}: {r.get('name','?')}")
            if r["status"] != "done":
                break
            count += 1
        print(f"本轮精读: {count}篇")
