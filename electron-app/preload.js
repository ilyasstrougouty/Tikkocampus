const { contextBridge, ipcRenderer } = require('electron');

// Expose a native Electron API to the frontend
contextBridge.exposeInMainWorld('electronAPI', {
  close: () => ipcRenderer.send('window-control', 'close'),
  minimize: () => ipcRenderer.send('window-control', 'minimize'),
  toggleMaximize: () => ipcRenderer.send('window-control', 'toggle-maximize')
});
