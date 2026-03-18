const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let pythonProcess;
let windowCreated = false;

function createWindow() {
  if (windowCreated) return;
  windowCreated = true;

  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    frame: false, // Frameless for premium look
    show: false,  // Hidden until backend is ready
    backgroundColor: '#1a1a1a',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'app_logo.ico')
  });

  // Load the frontend from local files (Static Mode)
  mainWindow.loadFile(path.join(__dirname, '..', 'web', 'index.html'));

  const apiUrl = 'http://127.0.0.1:8000';

  // Show the window immediately for a faster native feel
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Open external links in the default browser instead of the app window
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      event.preventDefault();
      require('electron').shell.openExternal(url);
    }
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      require('electron').shell.openExternal(url);
    }
    return { action: 'deny' };
  });

  // Robust polling for backend readiness (background logging)
  const pollBackend = () => {
    const request = http.get(`${apiUrl}/api/status`, (res) => {
      console.log('Backend API is responsive!');
    });

    request.on('error', (err) => {
      console.log('Backend API not ready yet, retrying in 1000ms...');
      setTimeout(pollBackend, 1000);
    });

    request.end();
  };

  pollBackend();

  mainWindow.on('closed', function () {
    mainWindow = null;
  });

  ipcMain.on('window-control', (event, action) => {
    console.log(`Received window control action: ${action}`);
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
  const pythonExec = path.resolve(__dirname, '..', 'venv', 'Scripts', 'python.exe');
  const appPath = path.resolve(__dirname, '..', 'app.py');
  const cwd = path.resolve(__dirname, '..');

  console.log(`Spawning Python: "${pythonExec}" "${appPath}"`);
  
  // To handle spaces in path on Windows without shell: true breaking everything:
  // We use the array form and escape/quote correctly.
  // Actually, spawn with array works fine on Windows if the elements themselves are the paths.
  pythonProcess = spawn(pythonExec, ['-u', appPath, '--server-only'], {
    cwd: cwd,
    shell: false, // Safer and handles array args better for paths with spaces
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });

  pythonProcess.stdout.on('data', (data) => {
    process.stdout.write(`[Python Stdout]: ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    process.stderr.write(`[Python Stderr]: ${data}`);
  });

  pythonProcess.on('error', (err) => {
    console.error(`FAILED TO START BACKEND: ${err.message}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python process closed with code ${code}`);
    if (mainWindow) app.quit();
  });
}

app.on('ready', () => {
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
