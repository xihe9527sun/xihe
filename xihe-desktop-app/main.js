const { app, BrowserWindow, Menu, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let deepCodeProcess;

const DEEPCODE_DIR = path.join(__dirname, '..', 'deepcode-clone', 'packages', 'cli');
const XIHE_DIR = 'F:\\SmartLegend\\Xihe';
const ICON_PATH = path.join(__dirname, 'icon.png');

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

app.whenReady().then(createWindow);
app.on('window-all-closed', () => {
  if (deepCodeProcess) deepCodeProcess.kill();
  app.quit();
});
