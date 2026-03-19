const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');

let mainWindow;
let pythonProcess;
let windowCreated = false;

// --- Production Diagnostic Logging ---
const logPath = path.join(app.getPath('userData'), 'startup-debug.log');
function logDebug(message) {
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] ${message}\n`;
  console.log(message);
  try {
    fs.appendFileSync(logPath, logMessage);
  } catch (err) {
    // Fallback if fs fails
  }
}

logDebug('--- App Startup Initiated ---');
logDebug(`isPackaged: ${app.isPackaged}`);
logDebug(`App Path: ${app.getAppPath()}`);

function createWindow() {
  logDebug('createWindow() called');
  if (windowCreated) return;
  windowCreated = true;

  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    frame: false,
    show: false,
    backgroundColor: '#1a1a1a',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'app_logo.ico')
  });

  const indexPath = path.join(__dirname, '..', 'web', 'index.html');
  logDebug(`Loading index.html from: ${indexPath}`);
  
  mainWindow.loadFile(indexPath).catch(err => {
    logDebug(`CRITICAL: failed to load index.html: ${err.message}`);
  });

  const apiUrl = 'http://127.0.0.1:8000';

  mainWindow.once('ready-to-show', () => {
    logDebug('Window ready-to-show event fired');
    mainWindow.show();
  });

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    logDebug(`ERROR: Frontend failed to load (${errorCode}): ${errorDescription}`);
  });

  // Robust polling for backend readiness
  const pollBackend = () => {
    const request = http.get(`${apiUrl}/api/status`, (res) => {
      logDebug('Backend API is responsive!');
    });

    request.on('error', (err) => {
      logDebug('Backend API not ready yet, retrying...');
      setTimeout(pollBackend, 1000);
    });

    request.end();
  };

  pollBackend();

  mainWindow.on('closed', function () {
    mainWindow = null;
  });

  ipcMain.on('window-control', (event, action) => {
    logDebug(`Received window control action: ${action}`);
    if (!mainWindow) return;
    switch (action) {
      case 'close':
        if (pythonProcess) pythonProcess.kill();
        app.quit();
        break;
      case 'minimize':
        mainWindow.minimize();
        break;
      case 'toggle-maximize':
        if (mainWindow.isMaximized()) {
          mainWindow.unmaximize();
        } else {
          mainWindow.maximize();
        }
        break;
    }
  });
}

function startPythonBackend() {
  let pythonExec;
  let args;
  let cwd;

  if (app.isPackaged) {
    const backendName = process.platform === 'win32' ? 'backend.exe' : 'backend';
    
    // PyInstaller directory mode structure: dist/backend/backend.exe
    // When moved to resources: resources/backend/backend.exe
    // BUT build_backend.py creates a folder named 'backend' INSIDE 'dist/backend'
    // Resulting in: resources/backend/backend/backend.exe
    const nestedPath = path.join(process.resourcesPath, 'backend', 'backend', backendName);
    const flatPath = path.join(process.resourcesPath, 'backend', backendName);
    
    if (fs.existsSync(nestedPath)) {
      pythonExec = nestedPath;
      logDebug(`Using nested backend path: ${pythonExec}`);
    } else {
      pythonExec = flatPath;
      logDebug(`Nested path not found, falling back to flat path: ${pythonExec}`);
    }

    args = ['--server-only']; 
    cwd = path.dirname(pythonExec);
  } else {
    pythonExec = path.resolve(__dirname, '..', 'venv', 'Scripts', 'python.exe');
    if (process.platform !== 'win32') {
        pythonExec = path.resolve(__dirname, '..', 'venv', 'bin', 'python');
    }
    const appPath = path.resolve(__dirname, '..', 'app.py');
    args = ['-u', appPath, '--server-only'];
    cwd = path.resolve(__dirname, '..');
  }

  logDebug(`Spawning Python Backend: "${pythonExec}"`);
  logDebug(`Current Working Directory: "${cwd}"`);
  
  pythonProcess = spawn(pythonExec, args, {
    cwd: cwd,
    shell: false,
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });

  pythonProcess.stdout.on('data', (data) => {
    logDebug(`[Python Stdout]: ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    logDebug(`[Python Stderr]: ${data}`);
  });

  pythonProcess.on('error', (err) => {
    logDebug(`FAILED TO START BACKEND: ${err.message}`);
  });

  pythonProcess.on('close', (code) => {
    logDebug(`Python process closed with code ${code}`);
    if (mainWindow) app.quit();
  });
}

app.on('ready', () => {
  logDebug('app ready event fired');
  startPythonBackend();
  createWindow();
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') {
    if (pythonProcess) pythonProcess.kill();
    app.quit();
  }
});

app.on('activate', function () {
  if (mainWindow === null) createWindow();
});

process.on('exit', () => {
    if (pythonProcess) pythonProcess.kill();
});
