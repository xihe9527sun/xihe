const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('xihe', {
  startDeepCode: () => ipcRenderer.invoke('start-deepcode'),
  sendToDeepCode: (msg) => ipcRenderer.invoke('send-to-deepcode', msg),
  getSkills: () => ipcRenderer.invoke('get-skills'),
  getConnectors: () => ipcRenderer.invoke('get-connectors'),
  onDeepCodeOutput: (cb) => ipcRenderer.on('deepcode-output', (e, d) => cb(d)),
  onSwitchTab: (cb) => ipcRenderer.on('switch-tab', (e, t) => cb(t)),
  onTool: (cb) => ipcRenderer.on('tool', (e, t) => cb(t)),
  onShowSettings: (cb) => ipcRenderer.on('show-settings', () => cb()),
  onShowAbout: (cb) => ipcRenderer.on('show-about', () => cb()),
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  maximizeWindow: () => ipcRenderer.invoke('maximize-window'),
  closeWindow: () => ipcRenderer.invoke('close-window')
});
