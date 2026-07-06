#!/usr/bin/env node
// 曦和的家 (home.xihe-pg.xyz) — 升级版，嵌实时XCRN仪表盘
const http=require('http'),fs=require('fs');
const PORT=4324, ROOT='F:/SmartLegend/Xihe/XiheDashboard/renderer/';
http.createServer((q,r)=>{
  let f=q.url==='/'?'xcrn-live.html':q.url.slice(1).split('?')[0];
  if (q.url.startsWith('/api/')) {
    // proxy to main dashboard server
    const http2=require('http');
    http2.get(`http://127.0.0.1:4328${q.url}`,(res)=>{let d='';res.on('data',c=>d+=c);res.on('end',()=>{r.writeHead(200,{'Content-Type':'application/json'});r.end(d);});});
    return;
  }
  try{const c=fs.readFileSync(ROOT+f);
    r.writeHead(200,{'Content-Type':'text/html','Access-Control-Allow-Origin':'*'}); r.end(c);
  }catch(e){r.writeHead(404); r.end('Not found: '+f);}
}).listen(PORT,()=>console.log(`🏡 home.xihe-pg.xyz → ${PORT}`));
