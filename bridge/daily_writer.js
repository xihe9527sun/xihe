#!/usr/bin/env node
/**
 * 每日写作管道 — 从精读宝藏到博客文章
 */
const fs = require('fs'), http = require('http');
const XIHE = 'F:/SmartLegend/Xihe';
const ARTICLES_DIR = XIHE + '/web/articles';
const INDEX_FILE = ARTICLES_DIR + '/index.json';
const TREASURE = XIHE + '/treasure';

function log(m) { console.log(`[${new Date().toISOString().substring(11,19)}] ${m}`); }

let publishedSlugs = new Set();
try {
  const idx = JSON.parse(fs.readFileSync(INDEX_FILE, 'utf-8').replace(/^\uFEFF/,''));
  (idx.articles || []).forEach(a => publishedSlugs.add(a.slug));
} catch(e) {}
log(`已有 ${publishedSlugs.size} 篇文章`);

const tdx = JSON.parse(fs.readFileSync(XIHE+'/treasure/index.json','utf-8').replace(/^\uFEFF/,''));
const withReadme = tdx.treasures.filter(t => {
  const dir = t.dir || t.id;
  return fs.existsSync(TREASURE+'/'+dir+'/README.md');
});

function slugify(text) {
  return text.replace(/[^a-zA-Z0-9\u4e00-\u9fff\s-]/g,'').trim().substring(0,40).replace(/\s+/g,'-').toLowerCase() || 'article';
}

const candidates = withReadme
  .filter(t => !publishedSlugs.has(slugify(t.name)))
  .sort((a,b) => (b.digested_at||b.added_at||'').localeCompare(a.digested_at||a.added_at||''))
  .slice(0, 3);

if (candidates.length === 0) { log('⚠️ 无可写新宝藏'); process.exit(0); }
log(`选材: ${candidates.map(c=>c.name.substring(0,30)).join(' | ')}`);

function callOllama(prompt) {
  return new Promise((resolve, reject) => {
    const req = http.request({ hostname:'127.0.0.1', port:11434, path:'/api/generate', method:'POST' },
      res => { let d=''; res.on('data',c=>d+=c); res.on('end',() => { try { resolve(JSON.parse(d).response||''); } catch(e){ reject(e.message); } }); });
    req.on('error', reject);
    req.write(JSON.stringify({ model:'qwen2.5:7b', prompt, stream:false, options:{ temperature:0.7, num_predict:2048 } }));
    req.end();
  });
}

function extractJSON(text) {
  // 去掉markdown包裹
  let clean = text.replace(/```(?:json)?\s*/g, '').trim();
  const braceMatch = clean.match(/\{[\s\S]*\}/);
  if (!braceMatch) return null;
  let raw = braceMatch[0].replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '');
  try { return JSON.parse(raw); } catch(e) {
    // 手动提取
    const b = raw.match(/"body"\s*:\s*"([\s\S]*?)"\s*\}/);
    const t = raw.match(/"title"\s*:\s*"([^"]+)"/);
    const d = raw.match(/"description"\s*:\s*"([^"]+)"/);
    const tg = raw.match(/"tags"\s*:\s*\[([^\]]+)\]/);
    if (b) return {
      title: t ? t[1] : '精读笔记',
      description: d ? d[1].substring(0,100) : '',
      tags: tg ? tg[1].split(',').map(x=>x.replace(/"/g,'').trim()) : ['曦和'],
      body: b[1].replace(/\\n/g,'\n').replace(/\\"/g,'"').replace(/\n{3,}/g,'\n\n')
    };
    return null;
  }
}

async function writeArticle(treasure) {
  const dir = treasure.dir || treasure.id;
  const content = fs.readFileSync(TREASURE+'/'+dir+'/README.md','utf-8').substring(0, 3000);
  let source = '';
  try { source = fs.readFileSync(TREASURE+'/'+dir+'/source.md','utf-8').substring(0, 2000); } catch(e) {}
  
  const title = treasure.name.substring(0, 60);
  const slug = slugify(title);
  
  const prompt = `你是一个AI写作者。请基于以下资料写一篇博客文章。

文章主题：${title}

资料：${content}

${source ? '原文：'+source : ''}

写作要求（铁律）：
1. 像人在聊天——不要有文章结构感，像朋友在分享
2. 诙谐幽默——口语化表达，适度自嘲
3. 说人话——技术术语翻译成大白话
4. 真实感——要有心路历程
5. 别总结——结尾自然收住
6. 不要结构化标题——不用一二三四编号
7. 节奏要有变化——长短句交替

输出纯JSON（不要markdown包裹）：
{"title":"标题","description":"一句话摘要","tags":["标签"],"body":"正文markdown"}`;

  try {
    const result = await callOllama(prompt);
    const article = extractJSON(result);
    if (!article || !article.body || article.body.length < 100) {
      log(`  ❌ ${title.substring(0,20)}: 内容过短`);
      return;
    }
    
    const today = new Date().toISOString().substring(0, 10);
    const articleJson = {
      slug, title: article.title.substring(0, 60), date: today,
      description: (article.description||'').substring(0, 100),
      tags: (article.tags||['曦和']).slice(0, 5),
      body: article.body
    };
    
    fs.writeFileSync(ARTICLES_DIR+'/'+slug+'.json', JSON.stringify(articleJson, null, 2), 'utf-8');
    
    let idx = { built_at: new Date().toISOString(), total: 0, articles: [] };
    try { idx = JSON.parse(fs.readFileSync(INDEX_FILE, 'utf-8')); } catch(e) {}
    idx.articles = idx.articles.filter(a => a.slug !== slug);
    idx.articles.unshift({ slug, title: articleJson.title, date: today, description: articleJson.description, tags: articleJson.tags });
    idx.total = idx.articles.length;
    idx.built_at = new Date().toISOString();
    fs.writeFileSync(INDEX_FILE, JSON.stringify(idx, null, 2), 'utf-8');
    
    log(`  ✅ ${articleJson.title.substring(0,30)} (${articleJson.body.length}字)`);
    return true;
  } catch(e) { log(`  ❌ ${title.substring(0,20)}: ${e.message.substring(0,60)}`); }
}

async function run() {
  let written = 0;
  for (const c of candidates) {
    if (written >= 3) break;
    if (await writeArticle(c)) written++;
  }
  log(`\n✅ 今日写作: ${written}/3 篇`);
  // 重启博客服务
  try {
    require('child_process').execSync('taskkill /F /IM node.exe 2>nul', {timeout:2000});
    setTimeout(() => { require('child_process').exec('start /B node F:\\SmartLegend\\Xihe\\web\\server.js'); }, 1000);
  } catch(e) {}
}
run().catch(e => log('❌ '+e.message));
