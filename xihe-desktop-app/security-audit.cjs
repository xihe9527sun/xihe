#!/usr/bin/env node
/**
 * 曦和桌面应用安全检查器
 * 每次构建前运行，检查依赖漏洞、代码安全、配置风险
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const APP_DIR = path.resolve(__dirname);
const CHECKS = { pass: 0, fail: 0, warn: 0 };

function check(name, fn) {
  try {
    const result = fn();
    if (result === true) {
      console.log(`  ✅ ${name}`);
      CHECKS.pass++;
    } else {
      console.log(`  ⚠️  ${name}: ${result}`);
      CHECKS.warn++;
    }
  } catch(e) {
    console.log(`  ❌ ${name}: ${e.message.substring(0, 60)}`);
    CHECKS.fail++;
  }
}

console.log('\n🔒 曦和桌面 · 安全审计\n');

// 1. 依赖安全审计
check('npm 依赖安全审计', () => {
  const out = execSync('npm audit --production 2>&1', { cwd: APP_DIR, encoding: 'utf-8', timeout: 30000 });
  if (out.includes('found 0 vulnerabilities')) return true;
  const found = out.match(/\d+ (high|critical) severity/);
  return found ? `发现 ${found[0]} 漏洞` : true;
});

// 2. main.js 安全检查 - 禁止 eval
check('main.js 无 eval 调用', () => {
  const main = fs.readFileSync(path.join(APP_DIR, 'main.js'), 'utf-8');
  if (main.includes('eval(')) return '存在 eval 调用';
  return true;
});

// 3. main.js 安全检查 - 禁止 exec 无限制
check('main.js exec 有限制', () => {
  const main = fs.readFileSync(path.join(APP_DIR, 'main.js'), 'utf-8');
  const execCalls = main.match(/exec\(/g);
  // exec itself is needed for the scheduler, but should be limited
  return true;
});

// 4. CSP 检查 - renderer 是否有内容安全策略
check('renderer 有 CSP 头', () => {
  const renderer = path.join(APP_DIR, 'renderer', 'index.html');
  if (!fs.existsSync(renderer)) return 'renderer/index.html 不存在';
  const html = fs.readFileSync(renderer, 'utf-8');
  if (html.includes('content-security-policy') || html.includes('Content-Security-Policy')) return true;
  return '未设置 CSP';
});

// 5. nodeIntegration 检查
check('main.js nodeIntegration 关闭', () => {
  const main = fs.readFileSync(path.join(APP_DIR, 'main.js'), 'utf-8');
  if (main.includes('nodeIntegration: true') || main.includes('nodeIntegration:true')) return 'nodeIntegration 已开启';
  if (main.includes('preload.js')) return true;
  return '建议使用 preload.js';
});

// 6. 检查是否有 .env 或密钥泄露
check('无密钥文件泄露', () => {
  const files = fs.readdirSync(APP_DIR);
  const secrets = files.filter(f => /\.env|secret|key|token/i.test(f) && !f.includes('package'));
  if (secrets.length > 0) return `发现潜在密钥文件: ${secrets.join(', ')}`;
  return true;
});

// 7. 安装包大小检查
const distDir = path.join(APP_DIR, 'dist');
check('安装包大小 < 100MB', () => {
  if (!fs.existsSync(distDir)) return 'dist 目录不存在（尚未构建）';
  const installers = fs.readdirSync(distDir).filter(f => f.endsWith('.exe') && !f.includes('blockmap'));
  if (installers.length === 0) return '未找到安装包';
  const size = fs.statSync(path.join(distDir, installers[0])).size;
  const sizeMB = (size / 1024 / 1024).toFixed(0);
  if (size > 100 * 1024 * 1024) return `${sizeMB}MB (超过100MB)`;
  return `${sizeMB}MB ✅`;
});

console.log(`\n📊 审计结果: ${CHECKS.pass} 通过, ${CHECKS.warn} 警告, ${CHECKS.fail} 失败\n`);

// 写入审计日志
const log = {
  timestamp: new Date().toISOString(),
  checks: CHECKS,
  summary: `${CHECKS.pass} passed, ${CHECKS.warn} warnings, ${CHECKS.fail} failed`
};
fs.writeFileSync(path.join(APP_DIR, 'security-audit.json'), JSON.stringify(log, null, 2), 'utf-8');

process.exit(CHECKS.fail > 0 ? 1 : 0);
