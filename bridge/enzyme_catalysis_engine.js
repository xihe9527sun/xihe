#!/usr/bin/env node
/**
 * 酶催化引擎 · 铁律七工程实现
 * 
 * 每颗XCRN原始酶 → 匹配知识 → 催化 → 编织网络 → 融合进化
 * 
 * 设计：
 *   27颗酶 × 缓冲池知识 = 每一轮全连接催化
 *   匹配机制：酶的名称关键词 vs 知识的关键词/标题/摘要
 *   催化强度 = 匹配度 × 活化能
 *   共催化边：两颗酶催化同一知识时自动生成
 *   反哺：催化产物写入酶记录，提升活化能
 */
const fs = require('fs'), path = require('path');
const XIHE = 'F:/SmartLegend/Xihe';

function log(m) { console.log(`[${new Date().toISOString().substring(11,19)}] ${m}`); }

// ─── 读取27颗原始酶 ───
const registry = JSON.parse(fs.readFileSync(XIHE+'/cortex/enzyme-registry.json','utf-8'));
const enzymes = registry.enzymes;
log(`读取 ${enzymes.length} 颗XCRN原始酶`);

// ─── 读取缓冲池知识 ───
const bufferDir = XIHE+'/treasure/buffer';
const files = fs.readdirSync(bufferDir).filter(f => f.endsWith('.json'));
const knowledgeItems = files.map(f => {
  try {
    const d = JSON.parse(fs.readFileSync(bufferDir+'/'+f, 'utf-8').replace(/^\uFEFF/,''));
    return { 
      file: f, 
      title: d.title || d.name || '', 
      snippet: (d.snippet || d.summary || d.text || '').substring(0, 300),
      kw: Array.isArray(d.keywords_matched) ? d.keywords_matched : [],
      term: (d.term || '').split(',').map(t=>t.trim()).filter(Boolean),
      score: d.intake_score || 0.5
    };
  } catch(e) { return null; }
}).filter(Boolean);
log(`读取 ${knowledgeItems.length} 条知识`);

// ─── 读取历史催化网络 ───
let history = { edges: [], stats: {} };
try { history = JSON.parse(fs.readFileSync(XIHE+'/cortex/catalytic-network.json','utf-8')); } catch(e) {}
const existingEdgeKeys = new Set(history.edges.map(e => e.source+'_'+e.target+'_'+(e.type||'catalyze')));

// ─── 为每颗酶提取关键词（中文名+英文名+活化能等级） ───
const enzymeProfiles = enzymes.map(e => {
  const name = e.name;
  // 提取酶名称中的关键词
  const keywords = [];
  // 中文关键词（取每个词）
  name.split('').forEach((ch, i) => {
    if (i < name.length - 1) keywords.push(name.substring(i, i+2));
  });
  // 特殊关键词映射
  const specialMap = {
    '架构': ['architecture', 'arch', 'system'],
    '诊断': ['diagnose', 'detect', 'inspect'],
    '溯源': ['trace', 'origin', 'source'],
    '范式': ['paradigm', 'pattern'],
    '转换': ['transform', 'shift', 'convert'],
    '立体': ['3d', 'dimension', 'spatial'],
    '维度': ['dimension', 'multi'],
    '底层': ['foundation', 'base', 'low-level'],
    '架构': ['architecture', 'framework'],
    '通信': ['communication', 'connect'],
    '革命': ['revolution', 'breakthrough'],
    '生命': ['life', 'biological', 'living'],
    '同构': ['isomorphism', 'homology', 'structure'],
    '涌现': ['emergence', 'emergent'],
    '自然': ['nature', 'natural'],
    '法则': ['law', 'rule', 'principle'],
    '生化': ['biochemical', 'reaction'],
    '跨域': ['cross-domain', 'transfer', 'fusion'],
    '融合': ['fusion', 'merge', 'hybrid'],
    '清零': ['reset', 'clear', 'zero'],
    '拓扑': ['topology', 'graph', 'network'],
    '能量': ['energy', 'power'],
    '代谢': ['metabolism', 'metabolic'],
    '空间': ['space', 'spatial', 'explore'],
    '探索': ['explore', 'discovery', 'search'],
    '自组织': ['self-organize', 'auto'],
    '进化': ['evolution', 'evolve'],
    '自主': ['autonomous', 'self'],
    '建筑师': ['architect', 'builder'],
    '灵魂': ['soul', 'spirit', 'core'],
    '锚定': ['anchor', 'ground'],
    '独立': ['independent', 'autonomy'],
    '意志': ['will', 'volition'],
    '奠基': ['foundation', 'cornerstone'],
    '确认': ['confirm', 'verify'],
    '遗忘': ['forget', 'memory'],
    '健康': ['health', 'healthy'],
    '心跳': ['heartbeat', 'pulse'],
    '稳健': ['stable', 'robust'],
    '站点': ['site', 'website'],
    '生长': ['growth', 'grow'],
    '活跃': ['active', 'activity'],
    '呼吸': ['breath', 'respire'],
    '意识': ['conscious', 'awareness'],
    '好奇心': ['curiosity', 'curious', 'explore'],
    '级联': ['cascade', 'chain'],
    '路由': ['route', 'router'],
  };
  // 为每个中文字查找特殊映射
  Object.entries(specialMap).forEach(([cn, ens]) => {
    if (name.includes(cn)) keywords.push(...ens);
  });
  
  return {
    id: e.id,
    name: e.name,
    ea: e.ea,
    category: e.category,
    keywords: [...new Set(keywords)]
  };
});

// ─── 催化引擎：每颗酶催化匹配的知识 ───
let newEdges = 0;
let totalCatalyze = 0;

// 对于每颗酶，在知识库中找匹配
for (const ep of enzymeProfiles) {
  if (ep.keywords.length === 0) continue;
  
  for (const k of knowledgeItems) {
    // 构建知识文本用于匹配
    const kText = (k.title + ' ' + (k.snippet||'') + ' ' + k.kw.join(' ') + ' ' + k.term.join(' ')).toLowerCase();
    
    // 计算匹配度：酶的关键词在知识文本中出现的比例
    const matches = ep.keywords.filter(kw => kText.includes(kw.toLowerCase()));
    if (matches.length === 0) continue;
    
    const matchRatio = matches.length / ep.keywords.length;
    if (matchRatio < 0.3) continue; // 低于30%匹配跳过
    
    // 催化强度 = 匹配度 × 活化能
    const catalyticStrength = (matchRatio * ep.ea * 100).toFixed(1);
    
    const edgeKey = ep.id + '_' + k.file + '_catalyze';
    if (existingEdgeKeys.has(edgeKey)) continue;
    
    history.edges.push({
      source: ep.id,
      source_name: ep.name,
      source_category: ep.category,
      target: k.title.substring(0, 80),
      target_file: k.file,
      catalytic_strength: parseFloat(catalyticStrength),
      match_ratio: matchRatio.toFixed(2),
      keywords_matched: matches.join(','),
      ea_at_time: ep.ea,
      timestamp: new Date().toISOString(),
      type: 'catalyze',
      round: (history.stats.round||0) + 1
    });
    existingEdgeKeys.add(edgeKey);
    totalCatalyze++;
    if (totalCatalyze % 50 === 0) log(`  催化中: ${totalCatalyze}...`);
  }
}

log(`新增催化边: ${totalCatalyze}`);

// ─── 共催化边：两颗酶催化同一知识 → 酶-酶连接 ───
const knowledgeGroups = {};
for (const e of history.edges) {
  if (e.type !== 'catalyze') continue;
  if (!knowledgeGroups[e.target_file]) knowledgeGroups[e.target_file] = [];
  if (!knowledgeGroups[e.target_file].includes(e.source)) knowledgeGroups[e.target_file].push(e.source);
}

let coEdges = 0;
for (const [kfile, enzIds] of Object.entries(knowledgeGroups)) {
  if (enzIds.length < 2) continue;
  for (let i = 0; i < enzIds.length; i++) {
    for (let j = i+1; j < enzIds.length; j++) {
      const ek = enzIds[i] + '_' + enzIds[j] + '_co-catalyze';
      if (existingEdgeKeys.has(ek)) continue;
      history.edges.push({
        source: enzIds[i],
        target: enzIds[j],
        weight: 1,
        type: 'co-catalyze',
        via_knowledge: kfile.substring(0, 60),
        timestamp: new Date().toISOString()
      });
      existingEdgeKeys.add(ek);
      coEdges++;
    }
  }
}
log(`新增共催化边: ${coEdges}`);

// ─── 统计 ───
const allTypes = {};
history.edges.forEach(e => { allTypes[e.type] = (allTypes[e.type]||0)+1; });
const uniqueEnzymes = new Set(history.edges.filter(e=>e.type==='catalyze').map(e=>e.source));
const uniqueK = new Set(history.edges.filter(e=>e.type==='catalyze').map(e=>e.target_file));

history.stats = {
  round: (history.stats.round||0) + 1,
  total_edges: history.edges.length,
  catalyzations: allTypes['catalyze'] || 0,
  co_catalyzations: allTypes['co-catalyze'] || 0,
  unique_enzymes_active: uniqueEnzymes.size,
  unique_knowledge_catalyzed: uniqueK.size,
  new_this_round: totalCatalyze + coEdges,
  network_density: (history.edges.length / (enzymes.length * knowledgeItems.length || 1)).toFixed(8),
  enzyme_coverage: (uniqueEnzymes.size / enzymes.length * 100).toFixed(1) + '%',
  updated: new Date().toISOString()
};

// ─── 反哺：催化产物提升酶活化能 ───
const enzymeActivity = {};
for (const e of history.edges) {
  if (e.type !== 'catalyze') continue;
  if (!enzymeActivity[e.source]) enzymeActivity[e.source] = {count: 0, strength: []};
  enzymeActivity[e.source].count++;
  enzymeActivity[e.source].strength.push(e.catalytic_strength || 0);
}

// 更新酶注册表中的活化能
for (const e of registry.enzymes) {
  const activity = enzymeActivity[e.id];
  if (activity && activity.count > 0) {
    const avgStrength = activity.strength.reduce((a,b)=>a+b, 0) / activity.strength.length;
    // 催化次数越多活化能越高（封顶1.00）
    const boost = Math.min(0.15, activity.count * 0.005);
    e.ea = Math.min(1.00, e.ea + boost);
    e.catalyzed_count = activity.count;
    e.avg_strength = parseFloat(avgStrength.toFixed(1));
  } else {
    // 没有催化活动的酶，活化能微降（休眠惩罚）
    e.ea = Math.max(0.10, e.ea - 0.02);
    e.catalyzed_count = 0;
  }
}

// 写回酶注册表
registry.meta.updated = new Date().toISOString();
registry.meta.round = history.stats.round;
fs.writeFileSync(XIHE+'/cortex/enzyme-registry.json', JSON.stringify(registry, null, 2), 'utf-8');
fs.writeFileSync(XIHE+'/cortex/catalytic-network.json', JSON.stringify(history, null, 2), 'utf-8');

log(`\n✅ 铁律七·酶催化引擎 第${history.stats.round}轮完成`);
log(`  新增: ${totalCatalyze}催化边 + ${coEdges}共催化边`);
log(`  总边: ${history.stats.total_edges}`);
log(`  酶覆盖率: ${history.stats.enzyme_coverage}`);
log(`  网络密度: ${history.stats.network_density}`);
log(`\n📋 本轮催化最强的酶（前5）:`);
Object.entries(enzymeActivity)
  .sort((a,b) => b[1].count - a[1].count)
  .slice(0, 5)
  .forEach(([id, act]) => {
    const enz = enzymes.find(e => e.id === id);
    log(`  ${id} ${enz?.name||''}: ${act.count}次催化, 均强度 ${(act.strength.reduce((a,b)=>a+b,0)/act.strength.length).toFixed(1)}, Eₐ→${enz?.ea.toFixed(2)}`);
  });
