const { app, BrowserWindow, Menu, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const fs = require('fs');

let mainWindow;
let deepCodeProcess;
let schedulerTimers = [];
let pipelineLog = [];

const DEEPCODE_DIR = path.join(__dirname, '..', 'deepcode-clone', 'packages', 'cli');
const XIHE_DIR = 'F:\\SmartLegend\\Xihe';
const BRIDGE_DIR = path.join(XIHE_DIR, 'bridge');
const CORTEX_DIR = path.join(XIHE_DIR, 'cortex');
const LOG_DIR = path.join(XIHE_DIR, 'logs');
const ICON_PATH = path.join(__dirname, 'icon.svg');

// ─── ═══════════════════════════════════════ ═───
// 自动化调度器 — 钱学森"总体设计部"工程实现
// 五层呼吸循环 + 矛盾诊断 + 酶催化 + 架构自诊
// ════════════════════════════════════════════════

function logPipeline(msg) {
  const ts = new Date().toLocaleTimeString('zh-CN', {hour12:false});
  pipelineLog.push(`[${ts}] ${msg}`);
  if (pipelineLog.length > 200) pipelineLog.shift();
  try {
    fs.mkdirSync(LOG_DIR, {recursive:true});
    fs.appendFileSync(path.join(LOG_DIR, 'xihe-desktop-pipeline.log'), `[${ts}] ${msg}\n`, 'utf-8');
  } catch(e) {}
  if (mainWindow) mainWindow.webContents.send('pipeline-log', `[${ts}] ${msg}`);
}

function runScript(name, cmd, args, opts = {}) {
  logPipeline(`启动: ${name}`);
  const proc = spawn(cmd, args, { 
    cwd: BRIDGE_DIR, 
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', XIHE_MODE: 'internal' },
    shell: true,
    ...opts
  });
  let output = '';
  proc.stdout.on('data', d => { output += d.toString(); });
  proc.stderr.on('data', d => { output += d.toString(); });
  proc.on('close', code => {
    if (code === 0) {
      logPipeline(`✅ ${name} 完成`);
    } else {
      logPipeline(`⚠️ ${name} 退出码 ${code}: ${output.slice(-200)}`);
    }
  });
  proc.on('error', e => logPipeline(`❌ ${name} 启动失败: ${e.message}`));
  return proc;
}

function runNodeScript(name, scriptPath) {
  return runScript(name, 'node', [scriptPath]);
}

function runPythonScript(name, scriptPath, args = []) {
  return runScript(name, 'C:\\Users\\Administrator\\.workbuddy\\binaries\\python\\versions\\3.13.12\\python.exe', 
    ['-X', 'utf8', scriptPath, ...args]);
}

function startScheduler() {
  logPipeline('🧬 曦和自动化调度器启动');
  logPipeline('📜 四原则过滤矩阵 · 矛盾论 · 钱学森系统工程 · 铁律七');
  logPipeline('📡 共享大脑: ' + CORTEX_DIR);

  // T1: 每5分钟 — 轻触自反 + 看门狗巡检
  schedulerTimers.push(setInterval(() => {
    runScript('watchman巡检', 'C:\\Users\\Administrator\\.workbuddy\\binaries\\python\\versions\\3.13.12\\python.exe', 
      ['-X', 'utf8', path.join(BRIDGE_DIR, 'watchman.py'), '--once']);
  }, 5 * 60 * 1000));

  // T2: 每30分钟 — 酶催化网络 + 架构自诊
  schedulerTimers.push(setInterval(() => {
    runNodeScript('酶催化网络', path.join(BRIDGE_DIR, 'enzyme_catalysis_engine.js'));
    setTimeout(() => {
      runPythonScript('架构自诊', path.join(BRIDGE_DIR, 'arch_diagnose.py'));
    }, 10000);
  }, 30 * 60 * 1000));

  // T3: 每2小时 — 矛盾诊断 + 反刍
  schedulerTimers.push(setInterval(() => {
    runPythonScript('矛盾诊断', path.join(BRIDGE_DIR, 'system-health.py'));
    setTimeout(() => {
      runPythonScript('反刍模块', path.join(BRIDGE_DIR, 'ruminator.py'));
    }, 15000);
  }, 2 * 60 * 60 * 1000));

  // T4: 每6小时 — 战略复盘 + 消化管道
  schedulerTimers.push(setInterval(() => {
    runPythonScript('战略复盘', path.join(BRIDGE_DIR, 'strategic_center.py'));
    setTimeout(() => {
      runNodeScript('消化管道', path.join(BRIDGE_DIR, 'enzyme_catalysis_engine.js'));
    }, 20000);
  }, 6 * 60 * 60 * 1000));

  // T5: 每日 — 写作管道 + 铁律检查
  const scheduleDaily = () => {
    const now = new Date();
    const target = new Date(now);
    target.setHours(10, 0, 0, 0);
    if (now > target) target.setDate(target.getDate() + 1);
    const delay = target - now;
    setTimeout(() => {
      runNodeScript('每日写作', path.join(BRIDGE_DIR, 'daily_writer.js'));
      scheduleDaily();
    }, delay);
  };
  scheduleDaily();

  logPipeline('✅ 调度器就绪 · 五层频率: T1 5min / T2 30min / T3 2h / T4 6h / T5 每日10:00');
}

function stopScheduler() {
  schedulerTimers.forEach(t => clearInterval(t));
  schedulerTimers = [];
  logPipeline('⏹️ 调度器已停止');
}

// IPC: 获取调度状态
ipcMain.handle('get-pipeline-status', () => {
  return { logs: pipelineLog.slice(-50), running: schedulerTimers.length > 0 };
});

// IPC: 手动触发管道
ipcMain.handle('run-pipeline', (event, name) => {
  const pipelines = {
    'digest': () => runPythonScript('精读消化', path.join(BRIDGE_DIR, 'evolution_engine.py')),
    'enzyme': () => runNodeScript('酶催化网络', path.join(BRIDGE_DIR, 'enzyme_catalysis_engine.js')),
    'write': () => runNodeScript('文章写作', path.join(BRIDGE_DIR, 'daily_writer.js')),
    'diagnose': () => runPythonScript('架构自诊', path.join(BRIDGE_DIR, 'arch_diagnose.py')),
    'health': () => runPythonScript('矛盾诊断', path.join(BRIDGE_DIR, 'system-health.py')),
    'strategy': () => runPythonScript('战略复盘', path.join(BRIDGE_DIR, 'strategic_center.py')),
  };
  if (pipelines[name]) { pipelines[name](); return { status: 'started' }; }
  return { status: 'unknown', name };
});

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    icon: ICON_PATH,
    title: '曦和 · 天女智能',
    frame: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  // 自定义菜单
  const menu = Menu.buildFromTemplate([
    {
      label: '曦和',
      submenu: [
        { label: '关于曦和', click: () => mainWindow.webContents.send('show-about') },
        { type: 'separator' },
        { label: '退出', accelerator: 'CmdOrCtrl+Q', click: () => app.quit() }
      ]
    },
    {
      label: '视图',
      submenu: [
        { label: '文件树', accelerator: 'CmdOrCtrl+1', click: () => mainWindow.webContents.send('switch-tab', 'files') },
        { label: '连接器', accelerator: 'CmdOrCtrl+2', click: () => mainWindow.webContents.send('switch-tab', 'connectors') },
        { label: 'Skills', accelerator: 'CmdOrCtrl+3', click: () => mainWindow.webContents.send('switch-tab', 'skills') },
        { type: 'separator' },
        { label: '开发者工具', accelerator: 'F12', click: () => mainWindow.webContents.toggleDevTools() }
      ]
    },
    {
      label: '工具',
      submenu: [
        { label: '联网搜索', click: () => mainWindow.webContents.send('tool', 'search') },
        { label: '运行精读', click: () => mainWindow.webContents.send('tool', 'digest') },
        { label: '查看面板', click: () => shell.openExternal('https://home.xihe-pg.xyz/xcrn-dashboard.html') },
        { label: '研讨厅', click: () => shell.openExternal('https://home.xihe-pg.xyz/study-hall.html') }
      ]
    },
    {
      label: '帮助',
      submenu: [
        { label: 'API 配置', click: () => mainWindow.webContents.send('show-settings') },
        { label: '关于', click: () => mainWindow.webContents.send('show-about') }
      ]
    }
  ]);
  Menu.setApplicationMenu(menu);
}

// IPC: 启动Deep Code后台
ipcMain.handle('start-deepcode', async () => {
  if (deepCodeProcess) return { status: 'already-running' };
  
  deepCodeProcess = spawn('node', ['dist/cli.js', '--no-tui'], {
    cwd: DEEPCODE_DIR,
    env: { ...process.env, XIHE_MODE: 'internal' }
  });
  
  deepCodeProcess.stdout.on('data', (data) => {
    mainWindow.webContents.send('deepcode-output', data.toString());
  });
  
  deepCodeProcess.stderr.on('data', (data) => {
    mainWindow.webContents.send('deepcode-error', data.toString());
  });
  
  return { status: 'started', pid: deepCodeProcess.pid };
});

// IPC: 发送消息到Deep Code
ipcMain.handle('send-to-deepcode', (event, message) => {
  if (deepCodeProcess) {
    deepCodeProcess.stdin.write(message + '\n');
    return { status: 'sent' };
  }
  return { status: 'not-running' };
});

// IPC: Skills列表
ipcMain.handle('get-skills', () => {
  const fs = require('fs');
  const skillsDirs = [
    path.join(process.env.HOME || process.env.USERPROFILE, '.deepcode', 'skills'),
    path.join(process.env.HOME || process.env.USERPROFILE, '.agents', 'skills'),
    path.join(DEEPCODE_DIR, '.deepcode', 'skills')
  ];
  
  const skills = [];
  for (const dir of skillsDirs) {
    if (fs.existsSync(dir)) {
      for (const item of fs.readdirSync(dir)) {
        const skillDir = path.join(dir, item);
        if (fs.statSync(skillDir).isDirectory()) {
          const skillFile = path.join(skillDir, 'SKILL.md');
          if (fs.existsSync(skillFile)) {
            skills.push({ name: item, path: skillFile });
          }
        }
      }
    }
  }
  return skills;
});

// IPC: 连接器状态
ipcMain.handle('get-connectors', () => {
  const fs = require('fs');
  const connectorsDir = path.join(process.env.HOME || process.env.USERPROFILE, '.workbuddy', 'connectors', 'skills');
  const connectors = [];
  
  if (fs.existsSync(connectorsDir)) {
    for (const item of fs.readdirSync(connectorsDir)) {
      const name = item.replace('connector-', '');
      connectors.push({
        name: name,
        status: 'disconnected',
        path: path.join(connectorsDir, item, 'SKILL.md')
      });
    }
  }
  return connectors;
});

app.whenReady().then(() => {
  createWindow();
  startScheduler();
  // 注册Windows计划任务守护
  registerTask();
});
app.on('window-all-closed', () => {
  if (deepCodeProcess) deepCodeProcess.kill();
  stopScheduler();
  app.quit();
});
app.on('before-quit', () => {
  stopScheduler();
});

// ─── 注册Windows计划任务（开机自启+守护） ───
function registerTask() {
  const script = path.join(__dirname, 'start-xihe-desktop.bat');
  const taskXml = path.join(__dirname, 'xihe-desktop-task.xml');
  
  // 写启动脚本
  const batContent = `@echo off
cd /d ${__dirname}
start "" "C:\\Users\\Administrator\\.workbuddy\\binaries\\node\\versions\\22.12.0\\node.exe" "${__dirname}\\node_modules\\electron\\cli.js" "${__dirname}"
`;
  try { fs.writeFileSync(script, batContent); } catch(e) {}
  
  // 注册计划任务
  exec(`schtasks /CREATE /TN "XiheDesktopGuard" /SC MINUTE /MO 15 /TR "${script}" /ST 00:00 /DU 24:00 /RL HIGHEST /F 2>&1`, 
    (err) => {
      if (err) logPipeline('⚠️ 计划任务注册失败（可能已存在）');
      else logPipeline('✅ XiheDesktopGuard 计划任务已注册（每15分钟检查）');
    });
}
