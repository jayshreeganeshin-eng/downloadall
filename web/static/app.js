// Universal Downloader - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initTabs();
    initForms();
    loadTasks();
    loadFiles();
});

// Tab Navigation
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            
            // Remove active class from all
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active class to selected
            btn.classList.add('active');
            document.getElementById(`${tabId}-tab`).classList.add('active');
        });
    });
}

// Initialize Forms
function initForms() {
    // Standard download form
    document.getElementById('download-form').addEventListener('submit', handleDownload);
    
    // Telegram config form
    document.getElementById('telegram-config-form').addEventListener('submit', handleTelegramConfig);
    
    // Telegram download form
    document.getElementById('telegram-download-form').addEventListener('submit', handleTelegramDownload);
    
    // Telegram clone form
    document.getElementById('telegram-clone-form').addEventListener('submit', handleTelegramClone);
}

// Handle Standard Download
async function handleDownload(e) {
    e.preventDefault();
    
    const url = document.getElementById('url').value;
    const platform = document.getElementById('platform').value;
    const quality = document.getElementById('quality').value;
    const audioOnly = document.getElementById('audio-only').checked;
    const playlist = document.getElementById('playlist').checked;
    
    const data = {
        platform: platform === 'auto' ? 'unknown' : platform,
        quality,
        audio_only: audioOnly,
        playlist
    };
    
    // Check if it's a username or URL
    if (url.startsWith('http')) {
        data.url = url;
    } else {
        data.username = url;
    }
    
    const resultDiv = document.getElementById('download-result');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const filesList = document.getElementById('files-list');
    
    resultDiv.classList.remove('hidden');
    progressFill.style.width = '0%';
    progressText.textContent = 'Starting download...';
    filesList.innerHTML = '';
    
    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            updateProgress(result.task);
            
            if (result.task.files_downloaded && result.task.files_downloaded.length > 0) {
                filesList.innerHTML = '<h4>Downloaded Files:</h4>' + 
                    result.task.files_downloaded.map(f => 
                        `<div class="file-item"><div class="file-name">${f}</div></div>`
                    ).join('');
            }
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError(error.message);
    }
}

// Update Progress Display
function updateProgress(task) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    progressFill.style.width = `${task.progress}%`;
    progressText.textContent = task.message;
    
    if (task.status === 'completed') {
        progressText.innerHTML = `<span class="alert-success">✅ ${task.message}</span>`;
    } else if (task.status === 'failed') {
        progressText.innerHTML = `<span class="alert-error">❌ ${task.message}</span>`;
    }
}

// Handle Telegram Configuration
async function handleTelegramConfig(e) {
    e.preventDefault();
    
    const apiId = document.getElementById('api-id').value;
    const apiHash = document.getElementById('api-hash').value;
    const phone = document.getElementById('phone').value;
    
    try {
        const response = await fetch('/api/telegram/configure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_id: apiId, api_hash: apiHash, phone })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Telegram connected successfully!');
            document.getElementById('telegram-status').classList.remove('hidden');
            checkTelegramStatus();
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError(error.message);
    }
}

// Handle Telegram Download
async function handleTelegramDownload(e) {
    e.preventDefault();
    
    const channel = document.getElementById('tg-channel').value;
    const limit = document.getElementById('tg-limit').value;
    
    try {
        const response = await fetch('/api/telegram/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel, limit })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`Download started: ${result.task.message}`);
            loadTasks();
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError(error.message);
    }
}

// Handle Telegram Clone
async function handleTelegramClone(e) {
    e.preventDefault();
    
    const source = document.getElementById('clone-source').value;
    const dest = document.getElementById('clone-dest').value;
    const type = document.getElementById('clone-type').value;
    const limit = document.getElementById('clone-limit').value;
    
    try {
        const response = await fetch('/api/telegram/clone', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source, dest, type, limit })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`Clone started: ${result.task.message}`);
            loadTasks();
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError(error.message);
    }
}

// Load Tasks
async function loadTasks() {
    try {
        const response = await fetch('/api/tasks');
        const result = await response.json();
        
        if (result.success) {
            const tasksList = document.getElementById('tasks-list');
            
            if (result.tasks.length === 0) {
                tasksList.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">No tasks yet</p>';
                return;
            }
            
            tasksList.innerHTML = result.tasks.map(task => `
                <div class="task-item status-${task.status}">
                    <div class="task-header">
                        <span class="task-platform">${task.platform.toUpperCase()}</span>
                        <span class="task-status status-${task.status}">${task.status}</span>
                    </div>
                    <div class="task-url">${task.url || task.username || 'N/A'}</div>
                    <div class="task-progress">
                        <strong>Progress:</strong> ${task.progress.toFixed(1)}% - ${task.message}
                    </div>
                    <div class="task-time">
                        <small>Created: ${new Date(task.created_at).toLocaleString()}</small>
                        ${task.completed_at ? `<small> | Completed: ${new Date(task.completed_at).toLocaleString()}</small>` : ''}
                    </div>
                    ${task.files_downloaded && task.files_downloaded.length > 0 ? 
                        `<div class="task-files"><small>Files: ${task.files_downloaded.length}</small></div>` : ''}
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

// Load Files
async function loadFiles() {
    try {
        const response = await fetch('/api/downloads');
        const result = await response.json();
        
        if (result.success) {
            const filesGrid = document.getElementById('files-grid');
            
            if (result.files.length === 0) {
                filesGrid.innerHTML = '<p style="color: var(--text-secondary); text-align: center; grid-column: 1/-1;">No files downloaded yet</p>';
                return;
            }
            
            filesGrid.innerHTML = result.files.map(file => {
                const icon = getFileIcon(file.name);
                const size = formatFileSize(file.size);
                
                return `
                    <div class="file-item">
                        <div class="file-icon">${icon}</div>
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${size}</div>
                        <a href="${file.url}" class="file-link" download>⬇️ Download</a>
                    </div>
                `;
            }).join('');
        }
    } catch (error) {
        console.error('Error loading files:', error);
    }
}

// Check Telegram Status
async function checkTelegramStatus() {
    try {
        const response = await fetch('/api/telegram/status');
        const result = await response.json();
        
        if (result.configured) {
            document.getElementById('telegram-status').classList.remove('hidden');
        } else {
            document.getElementById('telegram-status').classList.add('hidden');
        }
    } catch (error) {
        console.error('Error checking Telegram status:', error);
    }
}

// Helper Functions
function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
        mp4: '🎬', mkv: '🎬', avi: '🎬', mov: '🎬', webm: '🎬',
        mp3: '🎵', wav: '🎵', flac: '🎵', aac: '🎵',
        jpg: '🖼️', jpeg: '🖼️', png: '🖼️', gif: '🖼️', webp: '🖼️',
        pdf: '📄', doc: '📄', docx: '📄', txt: '📄'
    };
    return icons[ext] || '📁';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showSuccess(message) {
    showAlert(message, 'success');
}

function showError(message) {
    showAlert(message, 'error');
}

function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const card = document.querySelector('.card') || document.body;
    card.insertBefore(alertDiv, card.firstChild);
    
    setTimeout(() => alertDiv.remove(), 5000);
}

// Auto-refresh tasks every 5 seconds when on tasks tab
setInterval(() => {
    const tasksTab = document.getElementById('tasks-tab');
    if (tasksTab.classList.contains('active')) {
        loadTasks();
    }
}, 5000);
