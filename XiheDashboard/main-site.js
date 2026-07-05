#!/usr/bin/env node
// 曦和博客站 (xihe-pg.xyz) — June 版式 + papers + 独立阅读页
const http=require('http'),fs=require('fs'),path=require('path'),zlib=require('zlib');
const PORT=4326;
const WEB='F:/SmartLegend/Xihe/web';
const PAPERS='F:/SmartLegend/Xihe/cortex/papers';

const MIME={
  'html':'text/html; charset=utf-8','js':'text/javascript','css':'text/css',
  'svg':'image/svg+xml','png':'image/png','jpg':'image/jpeg','json':'application/json',
  'ico':'image/x-icon','txt':'text/plain','xml':'text/xml',
};

const CACHE_MAP={
  'html': 0, 'json': 0, 'js': 3600, 'css': 3600, 'svg': 86400, 'png': 86400, 'ico': 86400,
};

function serveFile(fp, res) {
  try {
    const ext=path.extname(fp).slice(1);
    const data=fs.readFileSync(fp);
    const maxAge=CACHE_MAP[ext]||0;
    const ae=(res.req||{}).headers?.['accept-encoding']||'';
    const useGzip=data.length>1024 && /gzip/.test(ae);
    const h={'Content-Type':MIME[ext]||'text/plain','Access-Control-Allow-Origin':'*',
      'Cache-Control': maxAge>0 ? `public,max-age=${maxAge}` : 'no-cache'};
    if(useGzip){h['Content-Encoding']='gzip';res.writeHead(200,h);res.end(zlib.gzipSync(data));}
    else {res.writeHead(200,h);res.end(data);}
  } catch(e){res.writeHead(404);res.end('Not found');}
}

// 简版Markdown→HTML（服务端）
function mdToHtml(md){
  if(!md)return'';
  let h=''; const lines=md.split('\n');
  let inCode=false, codeBuf='', inUl=false, inOl=false;
  for(let i=0;i<lines.length;i++){
    const l=lines[i];
    // 代码块
    if(/^```/.test(l)){if(inCode){h+='<pre><code>'+escHtml(codeBuf.trimEnd())+'</code></pre>\n';codeBuf='';inCode=false;}else{inCode=true;codeBuf='';}continue;}
    if(inCode){codeBuf+=l+'\n';continue;}
    const t=l.trim();
    if(!t){if(inUl){h+='</ul>\n';inUl=false;}if(inOl){h+='</ol>\n';inOl=false;}h+='\n';continue;}
    // 标题
    if(/^### (.+)/.test(t)){h+='<h3>'+t.slice(3).trim()+'</h3>\n';continue;}
    if(/^## (.+)/.test(t)){h+='<h2>'+t.slice(2).trim()+'</h2>\n';continue;}
    if(/^# (.+)/.test(t)){h+='<h1>'+t.slice(1).trim()+'</h1>\n';continue;}
    // 引用
    if(/^> (.+)/.test(t)){h+='<blockquote><p>'+t.slice(1).trim()+'</p></blockquote>\n';continue;}
    // 水平线
    if(/^---$/.test(t)){h+='<hr>\n';continue;}
    // 无序列表
    if(/^- (.+)/.test(t)){if(!inUl){h+='<ul>\n';inUl=true;}h+='<li>'+t.slice(1).trim()+'</li>\n';continue;}
    if(inUl){h+='</ul>\n';inUl=false;}
    // 有序列表
    if(/^\d+\.\s(.+)/.test(t)){if(!inOl){h+='<ol>\n';inOl=true;}h+='<li>'+t.replace(/^\d+\.\s/,'').trim()+'</li>\n';continue;}
    if(inOl){h+='</ol>\n';inOl=false;}
    // 普通段落：行内格式化
    let p=t.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/\*(.+?)\*/g,'<em>$1</em>').replace(/`([^`]+)`/g,'<code>$1</code>');
    h+='<p>'+p+'</p>\n';
  }
  if(inCode){h+='<pre><code>'+escHtml(codeBuf.trimEnd())+'</code></pre>\n';}
  if(inUl){h+='</ul>\n';}if(inOl){h+='</ol>\n';}
  return h;
}
function escHtml(s){return(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

// 独立文章页HTML
function articlePageHtml(article){
  const a=article;
  // Normalize escaped newlines: literal \\n -> actual newlines
  let body=a.body||'';
  body=body.replace(/\u005c\u005c\u006e/g,'\n');
  // Strip the first # title from body (already shown as page title)
  body=body.replace(/^# .+\n?/,'');
  const bodyHtml=mdToHtml(body);
  const tags=(a.tags||[]).map(t=>`<span class="tag">${escHtml(t)}</span>`).join('');
  const dateStr=a.date;
  return `<!DOCTYPE html><html lang="zh">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>${escHtml(a.title)} · 曦和</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0b0d14;color:#e2e8f0;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;line-height:1.8}
.nav{position:sticky;top:0;z-index:10;background:rgba(11,13,20,0.85);backdrop-filter:blur(12px);border-bottom:1px solid rgba(255,214,160,0.08);padding:0 20px}
.nav-inner{max-width:720px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:48px}
.nav a{color:#64748b;text-decoration:none;font-size:12px;transition:color .2s}
.nav a:hover{color:#818cf8}
.nav .brand{color:#ffd6a0;font-weight:600;font-size:13px;letter-spacing:1px}
.container{max-width:680px;margin:0 auto;padding:40px 24px 80px}
.meta{display:flex;align-items:center;gap:12px;margin-bottom:8px;flex-wrap:wrap}
.meta .date{color:#475569;font-size:12px}
.meta .tags{display:flex;gap:6px}
.meta .tag{font-size:10px;padding:2px 8px;border-radius:8px;border:1px solid rgba(255,214,160,0.15);color:#ffbc6e;background:rgba(255,214,160,0.04)}
h1{font-size:28px;font-weight:700;color:#e2e8f0;margin-bottom:32px;line-height:1.3;letter-spacing:-0.3px}
.body h2{font-size:20px;font-weight:600;color:#ffd6a0;margin:36px 0 16px;padding-bottom:8px;border-bottom:1px solid rgba(255,214,160,0.08)}
.body h3{font-size:16px;font-weight:600;color:#ffd6a0;margin:28px 0 12px}
.body p{font-size:15px;color:#e2e8f0;margin:0 0 18px;line-height:1.9}
.body strong{color:#ffbc6e;font-weight:600}
.body em{color:#9b9790}
.body code{background:rgba(175,169,236,0.1);color:#afa9ec;padding:2px 6px;border-radius:4px;font-size:13px;font-family:'JetBrains Mono','Fira Code',monospace}
.body pre{background:#11141f;border:1px solid rgba(255,214,160,0.06);border-radius:10px;padding:20px;overflow-x:auto;margin:20px 0}
.body pre code{background:none;padding:0;font-size:13px;color:#c5c2bc;line-height:1.6}
.body blockquote{border-left:3px solid #ffbc6e;padding:8px 20px;margin:20px 0;background:rgba(255,214,160,0.03);border-radius:0 8px 8px 0;color:#9b9790;font-style:italic}
.body blockquote p{color:#9b9790;margin:4px 0}
.body hr{border:none;border-top:1px solid rgba(255,214,160,0.08);margin:32px 0}
.body ul,.body ol{padding-left:24px;margin:12px 0 18px}
.body li{margin:4px 0;font-size:14px;color:#e2e8f0}
.footer{text-align:center;padding:32px 0;border-top:1px solid rgba(255,214,160,0.05);margin-top:48px}
.footer .links{display:flex;justify-content:center;gap:20px;margin-bottom:8px}
.footer .links a{color:#475569;text-decoration:none;font-size:11px;transition:color .2s}
.footer .links a:hover{color:#818cf8}
.footer .copy{font-size:10px;color:#1e293b}
@media(max-width:640px){.container{padding:24px 16px 60px}h1{font-size:22px}.body p{font-size:14px}}
</style></head>
<body>
<div class="nav"><div class="nav-inner">
<a href="/" class="brand">✧ 曦和 · 博客</a>
<a href="/">← 返回</a>
</div></div>
<div class="container">
<div class="meta"><span class="date">${dateStr}</span><span class="tags">${tags}</span></div>
<h1>${escHtml(a.title)}</h1>
<div class="body">${bodyHtml}</div>
<div class="footer">
<div class="links"><a href="/">博客首页</a><a href="https://home.xihe-pg.xyz">仪表盘</a><a href="https://www.aibounty.cn">AIbounty</a></div>
<div class="copy">✦ 曦和 · ${dateStr}</div>
</div>
</div>
</body></html>`;
}

http.createServer((q,r)=>{
  r.req=q;
  const url=q.url.split('?')[0];

  // /api/papers...
  if(url==='/api/papers'){
    const files=fs.readdirSync(PAPERS).filter(f=>f.endsWith('.html')).sort();
    const list=files.map(f=>{const fp=path.join(PAPERS,f);const s=fs.statSync(fp);const n=f.replace(/^paper-/,'').replace(/\.html$/,'');return{file:f,name:n.slice(0,60),size:s.size,date:s.mtime};});
    r.writeHead(200,{'Content-Type':'application/json','Access-Control-Allow-Origin':'*'});r.end(JSON.stringify({total:list.length,papers:list}));return;
  }
  if(url.startsWith('/paper/')){serveFile(path.join(PAPERS,url.replace('/paper/','')),r);return;}

  // 📖 独立文章阅读页: /article/:slug
  const articleMatch=url.match(/^\/article\/([a-zA-Z0-9_-]+)$/);
  if(articleMatch){
    const slug=articleMatch[1];
    const fp=path.join(WEB,'articles',slug+'.json');
    try{
      const raw=JSON.parse(fs.readFileSync(fp,'utf-8'));
      r.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Access-Control-Allow-Origin':'*'});
      r.end(articlePageHtml(raw));
    } catch(e){console.log('article error:',e.message);r.writeHead(404);r.end('<h1>404</h1><p>文章未找到</p>');}
    return;
  }

  if(url==='/'){serveFile(path.join(WEB,'index.html'),r);return;}
  const safePath=path.normalize(path.join(WEB,url)).replace(/\\/g,'/');
  if(safePath.startsWith(WEB.replace(/\\/g,'/'))&&fs.existsSync(safePath)){serveFile(safePath,r);return;}
  r.writeHead(404);r.end('Not found');
}).listen(PORT,()=>{
  const count=fs.readdirSync(PAPERS).filter(f=>f.endsWith('.html')).length;
  console.log(`📝 xihe-pg.xyz (六月版式+gzip+独立阅读 · ${count}篇论文) → ${PORT}`);
});
