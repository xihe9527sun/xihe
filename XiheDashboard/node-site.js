#!/usr/bin/env node
// 通信节点 (node.xihe-pg.xyz)
const http=require('http');
const PORT=4325;
http.createServer((q,r)=>{
  const d=JSON.stringify({
    status:'online',node:'xihe-comm',time:new Date().toISOString(),
    services:['event','heartbeat','cortex','space'],
    cortex:{treasures:194,heartbeats:'540k',enzymes:24,constraints:916}
  });
  r.writeHead(200,{'Content-Type':'application/json','Access-Control-Allow-Origin':'*'}); r.end(d);
}).listen(PORT,()=>console.log(`📡 node.xihe-pg.xyz → ${PORT}`));
