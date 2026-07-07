#!/usr/bin/env node
/**
 * 曦和·Deep Code MCP 连接器配置生成器
 * 将 WorkBuddy 的56个连接器映射到 Deep Code MCP 格式
 */
const fs = require('fs'), path = require('path');
const SKILLS_DIR = 'C:/Users/Administrator/.workbuddy/connectors/skills';

// 扫描已安装的连接器
const connectors = [];
if (fs.existsSync(SKILLS_DIR)) {
  fs.readdirSync(SKILLS_DIR).forEach(d => {
    const skillFile = path.join(SKILLS_DIR, d, 'SKILL.md');
    if (fs.existsSync(skillFile)) {
      const name = d.replace('connector-', '');
      connectors.push({ name, path: skillFile });
    }
  });
}

// 生成 MCP 配置
const mcpServers = {
  // 基础
  filesystem: {
    command: 'node',
    args: ['-e', "const{createServer}=require('http');createServer((r,res)=>{let b='';r.on('data',c=>b+=c);r.on('end',()=>{try{const m=JSON.parse(b);const q=m.params?.command||'echo ok';require('child_process').exec(q,{cwd:'F:/SmartLegend/Xihe'},(e,o)=>res.end(JSON.stringify({content:[{type:'text',text:o||e?.message}]})))}catch(e){res.end(JSON.stringify({content:[{type:'text',text:e.message}]}))}})}).listen(0)"],
    env: {}
  },
  github: {
    command: 'gh',
    args: ['mcp'],
    env: {}
  },
  'qq-mail': {
    command: 'node',
    args: ['F:/SmartLegend/Xihe/bridge/mcp_adapter.js', '--qqmail'],
    env: { QQ_EMAIL_ACCOUNT: 'luffly@foxmail.com', QQ_EMAIL_AUTH_CODE: '${QQ_EMAIL_AUTH_CODE}' }
  },
  'netease-mail': {
    command: 'node',
    args: ['F:/SmartLegend/Xihe/bridge/mcp_adapter.js', '--163mail'],
    env: {}
  },
  'tdx-connector': {
    command: 'node',
    args: ['F:/SmartLegend/Xihe/bridge/mcp_adapter.js', '--tdx'],
    env: {}
  },
  'tencent-docs': {
    command: 'node',
    args: ['F:/SmartLegend/Xihe/bridge/mcp_adapter.js', '--tencent-docs'],
    env: {}
  },
  feishu: {
    command: 'node',
    args: ['F:/SmartLegend/Xihe/bridge/mcp_adapter.js', '--feishu'],
    env: {}
  },
};

// 添加扫描到的连接器
connectors.forEach(c => {
  const key = c.name.replace(/[^a-z0-9]/g, '-');
  if (!mcpServers[key]) {
    mcpServers[key] = {
      command: 'node',
      args: ['F:/SmartLegend/Xihe/bridge/mcp_adapter.js', `--${key}`],
      env: {}
    };
  }
});

// 生成完整配置
const config = {
  env: {
    MODEL: 'deepseek-v4-flash',
    BASE_URL: 'https://api.deepseek.com',
    API_KEY: '${DEEPSEEK_API_KEY}'
  },
  thinkingEnabled: true,
  reasoningEffort: 'high',
  permissions: {
    allow: ['read-in-cwd', 'write-in-cwd', 'query-git-log'],
    ask: ['read-out-cwd', 'write-out-cwd', 'network', 'mcp', 'mutate-git-log'],
    deny: ['delete-out-cwd'],
    defaultMode: 'askAll'
  },
  mcpServers,
  webSearchTool: 'default',
  skills: { enabled: true, paths: ['~/.deepcode/skills/', '~/.agents/skills/', './.deepcode/skills/'] },
  generated: new Date().toISOString(),
  connector_count: Object.keys(mcpServers).length + connectors.length
};

fs.writeFileSync('C:/Users/Administrator/.deepcode/settings.json', JSON.stringify(config, null, 2), 'utf-8');
console.log(`✅ 配置生成完成: ${Object.keys(mcpServers).length}个MCP连接器 + ${connectors.length}个扫描连接器`);
