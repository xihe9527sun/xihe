#!/usr/bin/env python3
"""
进化引擎 · Evolution Engine v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
五篇合读后最顶级最有前景的方案：
让曦和从"在WorkBuddy会话中被盘古驱动进化"
转变为"被时钟驱动自我进化"。

核心能力：
  1. 每日自动取5篇未精读宝藏
  2. 调Ollama用四原则矩阵精读
  3. 精读结果写入README.md
  4. 自动反哺到cortex/insights + 每日计划
  5. 标记精读状态

调用方式：
  python evolution_engine.py              # 执行今日精读（取5篇）
  python evolution_engine.py --status      # 查看精读进度
  python evolution_engine.py --slot <id>   # 精读指定宝藏

集成方式：
  由每日健康报告完成后触发
  或由XiheWatchman每整点巡检时触发

位置: F:/SmartLegend/Xihe/bridge/evolution_engine.py
"""

import sys, os, json, time, re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

XIHE_ROOT = Path("F:/SmartLegend/Xihe")
BRIDGE_DIR = XIHE_ROOT / "bridge"
TREASURE_DIR = XIHE_ROOT / "treasure"
CORTEX_DIR = XIHE_ROOT / "cortex"
BJT = timezone(timedelta(hours=8))

# 引入模型提供商抽象层
sys.path.insert(0, str(BRIDGE_DIR))
from model_provider import ask

# ── 四原则精读Prompt模板 ──
PRINCIPLES_PROMPT = """你是一个精通架构设计的精读专家。请用四原则过滤矩阵精读以下论文内容。

论文标题: {title}
论文来源: {source}
论文内容:
{content}

请按以下格式输出精读结果（不要添加额外说明）：

## 第一遍：去粗取精 | 核心精华

### 三个真东西
列出3个最核心的发现/主张，每个用一句话+一句话解释。

### 对曦和的三条可迁移法则
| 法则 | 论文来源 | 曦和对位 |

## 第二遍：去伪存真 | 检验与质疑
提出1-2个质疑，用事实检验。给出"站得住/站不住"的结论。

## 第三遍：由此及彼 | 知识图谱连接
列出至少3条曦和已有系统与此论文的映射关系。
列出至少1条未被连接的新线索。

## 第四遍：由表及里 | 架构层洞见
表层是什么，底层是什么。
核心定理（一句话）。
今天就能反哺的一条具体建议。

## 精读评分
| 维度 | 分数 | 说明 |
|真知灼见度 | /10 | |
|曦和连接度 | /10 | |
|实践指导力 | /10 | |
|跨领域启发 | /10 | |"""

def get_pending(count=5):
    """获取N篇尚未精读的宝藏"""
    idx_path = TREASURE_DIR / "index.json"
    try:
        idx = json.loads(open(idx_path, "r", encoding="utf-8-sig").read())
    except:
        return []
    
    items = idx.get("treasures", [])
    pending = []
    for t in items:
        tid = t.get("id", "")
        tdir = TREASURE_DIR / (t.get("dir", tid))
        readme = tdir / "README.md"
        
        # 判断是否已精读（README不再包含自动模板特征）
        already_digested = False
        if readme.exists():
            content = open(readme, "r", encoding="utf-8").read()
            if "四原则过滤矩阵" in content or "精读评分" in content:
                already_digested = True
        
        if not already_digested:
            pending.append(t)
    
    return pending[:count]

def load_source(treasure):
    """加载宝藏的原文内容"""
    tid = treasure.get("id", "")
    tdir = TREASURE_DIR / (treasure.get("dir", tid))
    source_md = tdir / "source.md"
    source_html = tdir / "source.html"
    digest = tdir / "digest.json"
    
    content = ""
    if source_md.exists():
        content = open(source_md, "r", encoding="utf-8").read()
    elif source_html.exists():
        content = open(source_html, "r", encoding="utf-8").read()
    
    # 若有digest.json，附加nutrient数据
    if digest.exists():
        try:
            d = json.loads(open(digest, "r", encoding="utf-8-sig").read())
            if "nutrients" in d:
                content += "\n\n## 养分数据\n" + json.dumps(d["nutrients"], indent=2, ensure_ascii=False)
        except:
            pass
    
    return content[:8000]  # 限制长度

def generate_deep_read(treasure):
    """用Ollama生成精读"""
    title = treasure.get("name", "未知")
    source = treasure.get("source", "未知")
    content = load_source(treasure)
    
    if not content:
        return None, "原文不可读"
    
    prompt = PRINCIPLES_PROMPT.format(title=title, source=source, content=content)
    
    try:
        result = ask(prompt, system="你是曦和架构精读专家。输出要精炼、有洞见、直接能用。",
                    model="qwen2.5:7b", temperature=0.4, max_tokens=4096)
        if "error" in result:
            return None, result["error"]
        return result.get("text", ""), None
    except Exception as e:
        return None, str(e)

def write_readme(treasure_id, content):
    """将精读写入README.md"""
    tdir = TREASURE_DIR / treasure_id
    tdir.mkdir(parents=True, exist_ok=True)
    readme_path = tdir / "README.md"
    
    # 添加前导元信息
    header = f"""# {treasure_id}

> **精读日期**: {datetime.now(BJT).strftime('%Y-%m-%d %H:%M')}  
> **精读方式**: 进化引擎 v1 · 四原则过滤矩阵  
> **精读模型**: qwen2.5:7b

---
"""
    full = header + content
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(full)
    return True

def auto_feedback_to_cortex(treasure_id, treasure_name, readme_content):
    """精读后自动反哺"""
    sys.path.insert(0, str(BRIDGE_DIR))
    try:
        from feedback_cortex import auto_feedback, record_insight
        
        # 提取gaps和connections
        gaps = []
        connections = []
        if "反哺" in readme_content:
            for line in readme_content.split("\n"):
                if "→" in line and ("曦和" in line or "缺" in line or "还没有" in line):
                    gaps.append(line.strip())
                elif "→" in line and ("对应" in line or "映射" in line or "对位" in line):
                    connections.append(line.strip())
        
        # 提取评分
        scores = re.findall(r'\| *(\w+) *\| *(\d+)/10 *\|', readme_content)
        
        auto_feedback(treasure_id, treasure_name, connections[:3], gaps[:3])
        
        return {"connections": len(connections), "gaps": len(gaps), "scores": scores}
    except Exception as e:
        return {"error": str(e)}

def run_daily():
    """每日执行：取5篇 → 精读 → 写入 → 反哺"""
    print(f"\n{'='*50}")
    print(f"进化引擎 · {datetime.now(BJT).strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")
    
    pending = get_pending(5)
    if not pending:
        print("✅ 所有宝藏已精读完毕！")
        return
    
    print(f"今日待精读: {len(pending)} 篇")
    results = []
    
    for i, t in enumerate(pending):
        tid = t.get("id", "?")
        name = t.get("name", "?")
        print(f"\n--- [{i+1}/{len(pending)}] {name} ---")
        print(f"  加载原文...")
        
        content, err = generate_deep_read(t)
        if err:
            print(f"  ❌ 精读失败: {err}")
            results.append({"id": tid, "status": "failed", "error": err})
            continue
        
        # 写入
        write_readme(t.get("dir", tid), content)
        print(f"  ✅ 精读已写入 README.md")
        
        # 反哺
        feedback = auto_feedback_to_cortex(tid, name, content)
        print(f"  ✅ 反哺完成: {feedback.get('connections',0)}条连接, {feedback.get('gaps',0)}条差距")
        
        results.append({"id": tid, "status": "done"})
    
    print(f"\n{'='*50}")
    print(f"今日完成: {sum(1 for r in results if r['status']=='done')}/{len(results)}")
    print(f"剩余待精读: {len(get_pending(100))} 篇")

def show_status():
    """查看精读进度"""
    idx = json.loads(open(TREASURE_DIR / "index.json", "r", encoding="utf-8-sig").read())
    items = idx.get("treasures", [])
    
    total = len(items)
    digested = 0
    for t in items:
        tid = t.get("id", "")
        readme = TREASURE_DIR / (t.get("dir", tid)) / "README.md"
        if readme.exists():
            c = open(readme, "r", encoding="utf-8").read()
            if "四原则过滤矩阵" in c:
                digested += 1
    
    print(f"\n宝藏精读进度: {digested}/{total}")
    print(f"  已精读: {digested}")
    print(f"  剩余: {total - digested}")
    if total > 0:
        print(f"  完成率: {digested*100//total}%")

if __name__ == "__main__":
    if "--status" in sys.argv:
        show_status()
    elif "--slot" in sys.argv:
        idx = sys.argv.index("--slot")
        if idx + 1 < len(sys.argv):
            slot_id = sys.argv[idx + 1]
            # 查找并精读指定ID
            idx_data = json.loads(open(TREASURE_DIR / "index.json", "r", encoding="utf-8-sig").read())
            for t in idx_data.get("treasures", []):
                if t.get("id") == slot_id or t.get("dir") == slot_id:
                    content, err = generate_deep_read(t)
                    if err:
                        print(f"❌ {err}")
                    else:
                        write_readme(t.get("dir", t["id"]), content)
                        print(f"✅ {t['name']} 精读完成")
                    break
    else:
        run_daily()
