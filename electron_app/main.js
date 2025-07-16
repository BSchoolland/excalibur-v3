const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');

let mainWindow;
let stateFileWatcher = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 400,
    height: 140,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    maximizable: false,
    minimizable: false,
    fullscreenable: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  // Position window at bottom-right
  const { screen } = require('electron');
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;
  
  mainWindow.setPosition(width - 420, height - 160);

  // Make window visible on all workspaces and full screen
  mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  mainWindow.loadFile('renderer/index.html');

  // Enable click-through when not actively updating
  mainWindow.setIgnoreMouseEvents(false);

  // Hide from dock on macOS
  if (process.platform === 'darwin') {
    app.dock.hide();
  }
}

function startStateFileWatcher() {
  const stateFilePath = path.join(__dirname, 'overlay_state.json');
  
  // Watch for changes to the state file
  try {
    stateFileWatcher = fs.watchFile(stateFilePath, { interval: 100 }, () => {
      try {
        if (fs.existsSync(stateFilePath)) {
          const stateData = fs.readFileSync(stateFilePath, 'utf8');
          const state = JSON.parse(stateData);
          
          // Send update to renderer
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('status-update', state);
          }
        }
      } catch (error) {
        console.error('Error reading state file:', error);
      }
    });
    
    console.log('Watching for Python state updates...');
    
    // Try to read initial state if file exists
    if (fs.existsSync(stateFilePath)) {
      try {
        const stateData = fs.readFileSync(stateFilePath, 'utf8');
        const state = JSON.parse(stateData);
        
        // Wait a moment for renderer to be ready, then send initial state
        setTimeout(() => {
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('status-update', state);
          }
        }, 1000);
      } catch (error) {
        console.error('Error reading initial state file:', error);
      }
    }
    
  } catch (error) {
    console.error('Error setting up state file watcher:', error);
  }
}

function stopStateFileWatcher() {
  if (stateFileWatcher) {
    const stateFilePath = path.join(__dirname, 'overlay_state.json');
    fs.unwatchFile(stateFilePath);
    stateFileWatcher = null;
    console.log('Stopped watching state file');
  }
}

app.whenReady().then(() => {
  createWindow();
  
  // Start watching for Python state updates
  startStateFileWatcher();
});

app.on('window-all-closed', () => {
  stopStateFileWatcher();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('before-quit', () => {
  stopStateFileWatcher();
});

// IPC for receiving updates from background process (keep for backwards compatibility)
ipcMain.on('update-status', (event, data) => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('status-update', data);
  }
}); 