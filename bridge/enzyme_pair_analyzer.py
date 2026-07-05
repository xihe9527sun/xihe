#!/usr/bin/env python3
"""
酶对熔合分析器 · Enzyme Pair Analyzer v1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
分析cascade traces，识别高频搭档酶对，自动推荐熔合。

反哺来源：τ缩微V2 — LogicFolding逻辑折叠

输出：
  - 高频搭档排行榜（按共现频率排序）
  - 熔合推荐（哪些酶应该合并为一个复合酶）
  - cortex/enzyme-pairs.json 供调度器使用

位置: F:/SmartLegend/Xihe/bridge/enzyme_pair_analyzer.py
"""

import json, os
from pathlib import Path
from collections import Counter, defaultdict

TRACES_DIR = Path("F:/SmartLegend/Xihe/engine/traces")
OUTPUT_PATH = Path("F:/SmartLegend/Xihe/cortex/enzyme-pairs.json")

def analyze():
    traces = sorted(TRACES_DIR.glob("cascade_*.json"), reverse=True)[:50]  # 最近50条
    pairs = Counter()
    single = Counter()
    
    for tp in traces:
        try:
            data = json.loads(tp.read_text("utf-8"))
            enzymes = data.get("enzymes", data.get("cascade", []))
            if isinstance(enzymes, list):
                # 提取酶ID
                ids = []
                for e in enzymes:
                    eid = e.get("id") or e.get("enzyme") or (e if isinstance(e, str) else None)
                    if eid:
                        ids.append(eid)
                single.update(ids)
                # 统计共现对
                for i in range(len(ids)):
                    for j in range(i+1, len(ids)):
                        a, b = sorted([ids[i], ids[j]])
                        pairs[(a, b)] += 1
        except:
            pass
    
    if not pairs:
        return {"status": "no_data", "message": "无cascade trace数据"}
    
    total_traces = max(sum(pairs.values()), 1)
    
    # 熔合推荐逻辑
    recommendations = []
    for (a, b), count in pairs.most_common(20):
        freq = count / total_traces
        if freq >= 0.3:  # 共现率>=30% → 强烈推荐熔合
            rec = "strong"
        elif freq >= 0.15:
            rec = "suggest"
        else:
            rec = "observe"
        recommendations.append({
            "pair": [a, b],
            "cooccurrence": count,
            "frequency": round(freq, 2),
            "recommendation": rec,
        })
    
    result = {
        "analyzed_traces": len(traces),
        "total_pairs_detected": len(pairs),
        "recommendations": recommendations,
        "top_singles": dict(single.most_common(10)),
    }
    
    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return result

if __name__ == "__main__":
    r = analyze()
    print(json.dumps(r, indent=2, ensure_ascii=False))
