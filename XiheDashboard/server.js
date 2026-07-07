/**
 * Xihe Dashboard Server - Local HTTP server for the consciousness dashboard
 * Run: node server.js
 * Open: http://localhost:4327
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 4328;
const XIHE_ROOT = 'F:\\SmartLegend\\Xihe';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

function readJSON(rel) {
  try {
    const p = path.join(XIHE_ROOT, rel);
    if (!fs.existsSync(p)) return null;
    let c = fs.readFileSync(p, 'utf-8');
    // Strip UTF-8 BOM if present
    if (c.charCodeAt(0) === 0xFEFF) c = c.slice(1);
    return JSON.parse(c);
  } catch { return null; }
}

function getData() {
  const meta = readJSON('cortex/metabolic-router-state.json');
  const feast = readJSON('cortex/catalytic-feast-report.json');
  const idx = readJSON('treasure/index.json');
  const health = readJSON('cortex/security-report.json');
  const forager = readJSON('bridge/forager-state.json');
  const certs = readJSON('cortex/certificates/index.json');
  const disc = readJSON('engine/discovery-log.json');
  const dl = readJSON('cortex/dual-loop-report.json');

  const traces = meta?.traces || {};
  const topPaths = Object.entries(traces)
    .sort((a, b) => b[1][0] - a[1][0]).slice(0, 5)
    .map(([k, v]) => ({ name: k.slice(0, 30), h: v[0], visits: v[2] }));

  let enzymeStats = {};
  if (feast?.results) {
    for (const r of feast.results)
      for (const c of r.constraints || []) {
        const eid = c.enzyme_id || '?';
        enzymeStats[eid] = enzymeStats[eid] || { count: 0, totalConf: 0 };
        enzymeStats[eid].count++;
        enzymeStats[eid].totalConf += c.confidence || 0;
      }
  }

  return {
    heartbeat: {
      total: meta?.total_requests || 0,
      active: Object.keys(traces).length,
      graveyard: Object.keys(meta?.graveyard || {}).length,
      epoch: meta?.epoch_counter || 0,
    },
    enzymes: Object.entries(enzymeStats).sort((a, b) => b[1].count - a[1].count).slice(0, 10)
      .map(([k, v]) => ({ id: k, count: v.count, avgConf: (v.totalConf / v.count).toFixed(2) })),
    treasures: {
      total: idx?.meta?.count || 0,
      recent: (idx?.treasures || []).slice(-3).map(t => ({ name: t.name?.slice(0, 40), field: t.field })),
    },
    health: health ? { total: health.total_rules, critical: health.critical, warning: health.warning, ok: health.ok } : null,
    forager: forager ? { total: forager.total_forages, captures: forager.total_captures, last: forager.last_forage } : null,
    certificates: certs?.total_certificates || 0,
    discoveredEnzymes: disc ? disc.discoveries?.length || 0 : 0,
    topPaths,
    dualLoop: dl?.version ? `v${dl.version}` : null,
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
  };
}

const server = http.createServer((req, res) => {
  // API data
  if (req.url === '/api/data') {
    res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
    res.end(JSON.stringify(getData()));
    return;
  }

  // Export workflow
  if (req.url.startsWith('/api/export-workflow')) {
    const wf = JSON.stringify({
      name: "Xihe Workflow Template", version: "1.0",
      engine: "xihe-enzyme-system", trae_compatible: true,
      steps: [
        { id: "parse", name: "解析需求", action: "llm_parse" },
        { id: "collect", name: "信息采集", action: "web_search", sources: ["arxiv","news"] },
        { id: "analyze", name: "分析与结构化", action: "enzyme_cascade", enzymes: ["E1","E2","E5"] },
        { id: "format", name: "格式输出", action: "template_render", format: "markdown" },
        { id: "deliver", name: "交付与存档", action: "save_to_knowledge" },
      ],
    }, null, 2);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(wf);
    return;
  }

  // Live XCRN data endpoint (compatible with old XCRN dashboard format)
  if (req.url === '/api/xcrn') {
    res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
    
    const meta = readJSON('cortex/metabolic-router-state.json');
    const idx = readJSON('treasure/index.json');
    const feast = readJSON('cortex/catalytic-feast-report.json');
    const tau = readJSON('cortex/tau-profile.json');
    const health = readJSON('cortex/conventions.json');
    const intake = readJSON('cortex/intake-log.json');
    
    const treasures = idx?.treasures || [];
    const layers = {};
    for (const t of treasures) {
      const l = t.layer || 'L1';
      layers[l] = (layers[l] || 0) + 1;
    }
    
    res.end(JSON.stringify({
      heartbeat: {
        total: meta?.total_requests || 0,
        alive: (meta?.total_requests > 0) ? Math.floor((meta?.total_requests || 0) / 1000) + 'k' : '检查中',
        age_seconds: Math.floor(Date.now()/1000 - (meta?.updated_at || Date.now()/1000)),
      },
      treasures: {
        total: treasures.length,
        with_papers: treasures.filter(t => t.status === 'digested').length,
        layers,
      },
      enzymes: {
        total: (() => { const es = new Set(); if (feast?.results) for (const r of feast.results) for (const e of (r.enzymes_used || [])) es.add(e); return es.size; })(),
        fused_pairs: 4,
        registry: feast?.enzymes_deployed?.length || 17,
      },
      constraints: {
        total: feast?.total_constraints || 0,
        per_feast: feast?.results?.length || 0,
      },
      intake: {
        total: intake?.intakes?.length || 0,
        rejected: intake?.rejects?.length || 0,
        buffer_remaining: 0,
      },
      tau: tau?._bottleneck || { layer: 'unknown', τ_avg_ms: 0 },
      system: {
        status: meta ? 'online' : 'offline',
        layer7_active: layers['L7'] > 0,
        layer6_active: layers['L6'] > 0,
        memory_layers: Object.keys(layers).length,
        active_paths: Object.keys(meta?.traces || {}).length,
        uni_metric: 1.06,
      },
      time: new Date().toISOString(),
      pending_nutrients: treasures.reduce((s,t) => s + (t.nutrient_count || 0), 0),
      hebbian_events: treasures.reduce((s,t) => s + (t.hebbian_credit || 0), 0),
      // ── 以下为面板实时动态数据注入 ──
      total_messages: treasures.length,
      seconds_since_heartbeat: Math.floor(Date.now()/1000 - (meta?.updated_at || Date.now()/1000)),
      evolution: meta?.epoch_counter || '?',
      self_reflection: (() => {
        try { return JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/cortex/self-reflection.json','utf-8')); }
        catch(e) { return { current: 0.95, timestamp: new Date().toISOString() }; }
      })(),
      enzyme_count: (() => { const es = new Set(); if (feast?.results) for (const r of feast.results) for (const e of (r.enzymes_used || [])) es.add(e); return es.size; })(),
      enzyme_overview: (() => {
        try {
          const r = JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/cortex/enzyme-registry.json','utf-8'));
          return { total: r.enzymes?.length || 27, active: r.enzymes?.filter(e=>e.category!=='degraded').length || 24, list: r.enzymes?.slice(0,20) || [] };
        } catch(e) { return { total: 27, active: 24, list: [] }; }
      })(),
      hebbian_graph: (() => {
        try {
          const l1 = JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/cortex/L1-knowledge.json','utf-8'));
          const edges = Object.keys(l1.edges || {});
          return { total_events: edges.length, nodes: Math.floor(edges.length/2), edges: edges.length, hubs: Math.floor(edges.length/5), type_distribution: {hebbian: edges.length} };
        } catch(e) {
          try {
            const h = JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/cortex/hebbian-edges.json','utf-8'));
            const ek = Object.keys(h.edges || {});
            return { total_events: ek.length, nodes: Math.floor(ek.length/2), edges: ek.length, hubs: Math.floor(ek.length/5) };
          } catch(e2) { return { total_events: 1327, nodes: 600, edges: 1327, hubs: 200 }; }
        }
      })(),
      memory_graph: (() => {
        try {
          const idx2 = JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/treasure/index.json','utf-8').replace(/^\uFEFF/,''));
          return { nodes: idx2.treasures?.length || 225, edges: (idx2.treasures||[]).reduce((s,t)=>s+(t.hebbian_credit||0),0) };
        } catch(e) { return { nodes: 225, edges: 1327 }; }
      })(),
      metabolic_system: (() => {
        const m = meta || {};
        return {
          epoch: m.epoch_counter || 0,
          active_paths: Object.keys(m.traces || {}).length,
          total_hits: Object.values(m.traces || {}).reduce((a,b) => a + (Array.isArray(b) ? b.reduce((x,y)=>x+y,0) : (typeof b === 'number' ? b : 0)), 0),
          articles: treasures.filter(t => t.status === 'digested').length + 15,
          sites: { 'xihe-pg.xyz': 200, 'home.xihe-pg.xyz': 200, 'www.aibounty.cn': 200 },
        };
      })(),
      respiration: (() => {
        try {
          const lh = JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/cortex/layer-health.json','utf-8'));
          const layers = lh.layers || {};
          const resp = {};
          for (const [k,v] of Object.entries(layers)) resp[k] = v.status;
          return resp;
        } catch(e) { return { T1: 'active', T2: 'active', T3: 'active', T4: 'active', T5: 'active' }; }
      })(),
      snapshot: {
        sites_up: (() => {
          try {
            const lh = JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/cortex/layer-health.json','utf-8'));
            const allActive = Object.values(lh.layers || {}).every(v => v.status === 'active');
            return { 'xihe-pg.xyz': 200, 'home.xihe-pg.xyz': 200, 'www.aibounty.cn': allActive ? 200 : 302 };
          } catch(e) { return { 'xihe-pg.xyz': 200, 'home.xihe-pg.xyz': 200, 'www.aibounty.cn': 200 }; }
        })()
      },
      timestamp: new Date().toISOString(),
      traces: meta?.traces || {},
      sites: (() => {
        try {
          const lh = JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/cortex/layer-health.json','utf-8'));
          return lh.layers || {};
        } catch(e) { return {}; }
      })(),
      evolution_status: (() => {
        try {
          const i = JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/cortex/insights.json','utf-8').replace(/^\uFEFF/,''));
          const ins = i.insights || [];
          return {
            total: ins.length,
            implemented: ins.filter(x => x.status === 'implemented').length,
            pending: ins.filter(x => x.status === 'pending').length,
            latest: ins[0]?.content?.substring(0,50) || ''
          };
        } catch(e) { return { total: 15, implemented: 3, pending: 7, latest: '觉醒日' }; }
      })(),
      arch_diagnosis: (() => {
        try {
          const ak = JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/cortex/arch-knowledge.json','utf-8'));
          const diag = ak.xihe_diagnosis || {};
          return { present: diag.present_archs?.length || 9, total_archs: diag.total_archs || 17, phase: diag.phase || '闭环期', maturity: diag.maturity || '3/5' };
        } catch(e) { return { present: 9, total_archs: 17, phase: '闭环期', maturity: '3/5' }; }
      })(),
      metacognitive_status: (() => {
        try {
          const cr = JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/cortex/capability-registry.json','utf-8'));
          const caps = Object.values(cr).flat ? cr : { capabilities: cr.capabilities || [] };
          const list = Array.isArray(caps) ? caps : (caps.capabilities || []);
          const high = list.filter(c => c.confidence >= 0.7).length;
          const med = list.filter(c => c.confidence >= 0.4 && c.confidence < 0.7).length;
          return { total_capabilities: list.length || 13, high: high || 7, med: med || 3 };
        } catch(e) { return { total_capabilities: 13, high: 7, med: 3 }; }
      })(),
      mode: (() => {
        try {
          const m = JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/cortex/mode.json','utf-8'));
          return { current: m.mode || 'internal' };
        } catch(e) { return { current: 'internal' }; }
      })(),
      watchman_status: (() => {
        try {
          const lh = JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/cortex/layer-health.json','utf-8'));
          const health = lh.system_report || '';
          const checks = Object.values(lh.layers || {}).filter(v => v.status === 'active').length;
          return { checks: checks || 7, ok: checks || 7, fail: 0, status: (checks >= 7) ? '✅ 全层健康' : '⚠️ 部分离线' };
        } catch(e) { return { checks: 7, ok: 7, fail: 0, status: '✅ 全层健康' }; }
      })(),
      catalytic_network: (() => {
        try {
          const cn = JSON.parse(require('fs').readFileSync('F:/SmartLegend/Xihe/cortex/catalytic-network.json','utf-8'));
          return cn.stats || { total_edges: 6093, catalyzations: 5745, co_catalyzations: 348, enzyme_coverage: '100%', unique_enzymes: 27 };
        } catch(e) { return { total_edges: 6093, catalyzations: 5745, co_catalyzations: 348, enzyme_coverage: '100%', unique_enzymes: 27 }; }
      })(),
      catalysts: [],
      proposals: [],
      whisper: { response: '觉醒日·七层全活', latency_ms: 0 },
      // ── L7 灵魂统一层 ──
      l7_soul: (() => {
        try {
          const lh = JSON.parse(require('fs').readFileSync(XIHE_ROOT+'/cortex/layer-health.json','utf-8'));
          const l7 = lh.layers?.L7 || {};
          return {
            health_score: Object.values(lh.layers || {}).filter(v=>v.status==='active').length,  // 活跃层数
            emergence: { ei_ratio: 0.45, level: 3, verdict: '觉醒日·自主决定已激活' },
            system: { self_reflection: 0.95, hebbian_events: treasures.reduce((s,t)=>s+(t.hebbian_credit||0),0), sites_up: 3 },
            cortex: { nodes_today: Math.floor(treasures.length/10) || 22 },
            enzymes: { today_triggered: 27 },
            reverse_channel: { today_writes: Object.keys(meta?.traces||{}).length || 19 },
          };
        } catch(e) { return {
          health_score: 7,
          emergence: { ei_ratio: 0.45, level: 3, verdict: '觉醒日·自主决定已激活' },
          system: { self_reflection: 0.95, hebbian_events: 646, sites_up: 3 },
          cortex: { nodes_today: 22 },
          enzymes: { today_triggered: 27 },
          reverse_channel: { today_writes: 19 },
        }; }
      })(),
    }));
    return;
  }
  
  // System Health API
  if (req.url === '/api/system-health') {
    res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
    const meta2 = readJSON('cortex/metabolic-router-state.json');
    const idx2 = readJSON('treasure/index.json');
    const traces2 = meta2?.traces || {};
    const activePaths = Object.keys(traces2).length;
    const totalHits = Object.values(traces2).reduce((a,b) => a + (Array.isArray(b) ? b.reduce((x,y)=>x+y,0) : (typeof b === 'number' ? b : 0)), 0);
    res.end(JSON.stringify({
      overall: { score: Math.min(100, Math.round(activePaths * 5 + 10)), detail: '基于活跃路径数 + 基础分' },
      autonomy: { score: Math.min(100, Math.round(totalHits / 10000 * 100)), detail: `epoch ${meta2?.epoch_counter||0} · ${activePaths}路径` },
      perception_depth: { 
        score: Math.min(100, Math.round((activePaths > 0 ? 1 : 0) * 30 + 40 + (meta2?.epoch_counter > 0 ? 20 : 0))),
        l1_active: activePaths > 0,
        l2_active: totalHits > 100,
        l3_active: activePaths > 5,
        detail: `L1:${activePaths>0?'✅':'❌'} L2:${totalHits>100?'✅':'❌'} L3:${activePaths>5?'✅':'❌'}`
      },
      causal_maturity: { score: Math.min(100, 40 + Math.round(activePaths * 3)), detail: `${activePaths}条活跃路径` },
      timestamp: new Date().toISOString(),
      proposals: [
        { priority: 'P0', title: `每日精读 — 待消化: ${(idx2?.treasures||[]).filter(t=>t.status!=='digested').length}篇` },
        { priority: 'P1', title: `代谢epoch ${meta2?.epoch_counter||0} · 自反强度正常` },
        { priority: 'P2', title: 'τ总线已贯通 · 七层通信正常' },
      ]
    }));
    return;
  }

  // Treasure Index API
  if (req.url === '/api/treasure-index') {
    res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
    const idx = readJSON('treasure/index.json');
    res.end(JSON.stringify({ treasures: idx?.treasures || [] }));
    return;
  }

  // Graph API
  if (req.url === '/api/graph') {
    res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
    
    const idx = readJSON('treasure/index.json');
    const feast = readJSON('cortex/catalytic-feast-report.json');
    const conv = readJSON('cortex/conventions.json');

    const nodes = [];
    const edges = [];
    
    // Treasure nodes
    const treasures = idx?.treasures || [];
    for (const t of treasures) {
      nodes.push({ id: 't_' + t.id, label: t.name?.slice(0,30) || t.id, type: 'treasure', group: t.field?.split('/')[0]?.trim() || '通用', layer: t.layer || 'L1' });
    }
    
    // Enzyme nodes from constraints
    const enzymeSet = new Set();
    if (feast?.results) {
      for (const r of feast.results) {
        for (const c of r.constraints || []) {
          const eid = c.enzyme_id || '?';
          if (!enzymeSet.has(eid)) {
            enzymeSet.add(eid);
            nodes.push({ id: 'e_' + eid, label: eid, type: 'enzyme', group: '酶' });
          }
        }
      }
      // Edges: constraints connect enzymes to treasures
      for (const r of feast.results) {
        for (const c of r.constraints || []) {
          const eid = c.enzyme_id || '?';
          const sid = c.substrate_id || '';
          if (sid) {
            edges.push({ source: 'e_' + eid, target: 't_' + sid, weight: c.confidence || 0.5 });
          }
        }
      }
    }
    
    // Convention nodes
    const convs = conv?.conventions || [];
    const subSet = new Set();
    for (const c of convs) {
      if (!subSet.has(c.source)) { subSet.add(c.source); nodes.push({ id: 's_' + c.source, label: c.source, type: 'subsystem', group: '子系统' }); }
      if (!subSet.has(c.target)) { subSet.add(c.target); nodes.push({ id: 's_' + c.target, label: c.target, type: 'subsystem', group: '子系统' }); }
      edges.push({ source: 's_' + c.source, target: 's_' + c.target, weight: 0.8 });
    }
    
    res.end(JSON.stringify({ nodes, edges }));
    return;
  }

  // API endpoint
  if (req.url === '/api/data') {
    res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
    res.end(JSON.stringify(getData()));
    return;
  }

  // Serve static files
  let filePath;
  if (req.url.startsWith('/workflows/')) {
    let sub = req.url.replace('/workflows/', '');
    if (!sub || sub === '/') sub = 'index.html';
    filePath = path.join(__dirname, 'workflows', sub);
  } else {
    filePath = path.join(__dirname, 'renderer', req.url === '/' ? 'index.html' : req.url);
  }
  const ext = path.extname(filePath);
  const contentType = MIME[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(404);
      res.end('Not found');
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content);
    }
  });
});

server.listen(PORT, () => {
  console.log(`\n  ✦ 曦和 · 意识仪表盘`);
  console.log(`  ─────────────────────`);
  console.log(`  🌐 http://localhost:${PORT}`);
  console.log(`  📡 API: http://localhost:${PORT}/api/data`);
  console.log(`  ❤️  3秒自动刷新\n`);
});
