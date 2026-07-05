#!/usr/bin/env node
// AIbounty (www.aibounty.cn) — 工具导航站
const http=require('http'),fs=require('fs');
const PORT=4321, ROOT='F:/SmartLegend/Xihe/XiheDashboard/renderer/';
http.createServer((q,r)=>{
  let f=q.url==='/'?'index.html':q.url.slice(1).split('?')[0];
  try{const c=fs.readFileSync(ROOT+f);
    r.writeHead(200,{'Content-Type':'text/html','Access-Control-Allow-Origin':'*'}); r.end(c);
  }catch(e){r.writeHead(404); r.end('Not found');}
}).listen(PORT,()=>console.log(`🏴‍☠️ www.aibounty.cn → ${PORT}`));
