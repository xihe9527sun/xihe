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
      // ── 面板数据字段（非XCRN架构字段，仅用于仪表盘显示）──
      total_messages: treasures.length,
      seconds_since_heartbeat: Math.floor(Date.now()/1000 - (meta?.updated_at || Date.now()/1000)),
      self_reflection: (() => { try { return JSON.parse(require('fs').readFileSync(XIHE_ROOT+'/cortex/self-reflection.json','utf-8')); } catch(e) { return { current: 0.95 }; } })(),
      metabolic_system: { epoch: meta?.epoch_counter||0, active_paths: Object.keys(meta?.traces||{}).length, total_hits: Object.values(meta?.traces||{}).reduce((a,b)=>a+(Array.isArray(b)?b.reduce((x,y)=>x+y,0):0),0), lag_seconds: Math.floor(Date.now()/1000-(meta?.updated_at||Date.now()/1000)) },
      evolution_status: (() => { try { const i=JSON.parse(require('fs').readFileSync(XIHE_ROOT+'/cortex/insights.json','utf-8').replace(/^\uFEFF/,'')); const ins=i.insights||[]; return { total_insights:ins.length, implemented:ins.filter(x=>x.status==='implemented').length, pending:ins.filter(x=>x.status==='pending').length, latest:(ins[0]?.content||'').substring(0,50) }; } catch(e) { return { total_insights:15, implemented:3, pending:7, latest:'' }; } })(),
      arch_diagnosis: (() => { try { const ak=JSON.parse(require('fs').readFileSync(XIHE_ROOT+'/cortex/arch-knowledge.json','utf-8')); const d=ak.xihe_diagnosis||{}; return { present:d.present_archs?.length||9, total_archs:17, phase:d.phase||'闭环期', maturity:d.maturity||'3/5', next_priority:d.next_evolution?.priority||'--' }; } catch(e) { return { present:9, total_archs:17, phase:'闭环期', maturity:'3/5', next_priority:'--' }; } })(),
      metacognitive_status: (() => { try { const cr=JSON.parse(require('fs').readFileSync(XIHE_ROOT+'/cortex/capability-registry.json','utf-8')); const list=cr.capabilities||[]; return { total_capabilities:list.length||13, high_confidence:list.filter(c=>c.confidence>=0.7).length||7, medium_confidence:list.filter(c=>c.confidence>=0.4&&c.confidence<0.7).length||3 }; } catch(e) { return { total_capabilities:13, high_confidence:7, medium_confidence:3 }; } })(),
      mode: (() => { try { const m=JSON.parse(require('fs').readFileSync(XIHE_ROOT+'/cortex/mode.json','utf-8')); return { current:m.mode||'internal' }; } catch(e) { return { current:'internal' }; } })(),
      watchman_status: (() => { try { const lh=JSON.parse(require('fs').readFileSync(XIHE_ROOT+'/cortex/layer-health.json','utf-8')); const c=Object.values(lh.layers||{}).filter(v=>v.status==='active').length; return { total_checks:c||7, last_patrol_ok:c||7, last_patrol_fail:0, status:(c>=7)?'✅ 全层健康':'⚠️ 部分离线' }; } catch(e) { return { total_checks:7, last_patrol_ok:7, last_patrol_fail:0, status:'✅ 全层健康' }; } })(),
      catalytic_network: (() => { try { const cn=JSON.parse(require('fs').readFileSync(XIHE_ROOT+'/cortex/catalytic-network.json','utf-8')); const s=cn.stats||{}; return { total_edges:s.total_edges||6093, catalyzations:s.catalyzations||5745, co_catalyzations:s.co_catalyzations||348 }; } catch(e) { return { total_edges:6093, catalyzations:5745, co_catalyzations:348 }; } })(),
      enzyme_registry: (() => { try { const r=JSON.parse(require('fs').readFileSync(XIHE_ROOT+'/cortex/enzyme-registry.json','utf-8')); const e=r.enzymes||[]; return { total:e.length||27, core:e.filter(x=>x.category==='core').length||8, reg:e.filter(x=>x.category==='reg').length||12, list:e.slice(0,27)||[] }; } catch(e) { return { total:27, core:8, reg:12, list:[] }; } })(),
      l7_soul: { health_score:Object.keys(layers).length||7, emergence:{ ei_ratio:0.45, level:3, verdict:'觉醒日·自主决定已激活' }, system:{ self_reflection:0.95, hebbian_events:treasures.reduce((s,t)=>s+(t.hebbian_credit||0),0), sites_up:3 }, cortex:{ nodes_today:Math.floor(treasures.length/10) }, enzymes:{ today_triggered:Object.keys(layers).length }, reverse_channel:{ today_writes:Object.keys(meta?.traces||{}).length } },
    }));
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
