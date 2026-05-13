// Universal Downloader - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Tab Navigation
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            
            // Update buttons
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Update content
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `${tabId}-tab`) {
                    content.classList.add('active');
                }
            });
            
            // Refresh files if files tab
            if (tabId === 'files') {
                loadFiles();
            }
        });
    });

    // Download Button
    const downloadBtn = document.getElementById('download-btn');
    downloadBtn.addEventListener('click', startDownload);

    // Clone Button
    const cloneBtn = document.getElementById('clone-btn');
    cloneBtn.addEventListener('click', cloneChannel);

    // Refresh Files Button
    const refreshFilesBtn = document.getElementById('refresh-files-btn');
    refreshFilesBtn.addEventListener('click', loadFiles);

    // Auto-refresh downloads every 2 seconds
    setInterval(loadDownloads, 2000);

    // Initial load
    loadDownloads();
});

// Start Download
async function startDownload() {
    const url = document.getElementById('url').value.trim();
    const quality = document.getElementById('quality').value;
    const platform = document.getElementById('platform').value;
    const audioOnly = document.getElementById('audio-only').checked;
    const isPlaylist = document.getElementById('is-playlist').checked;

    if (!url) {
        showNotification('Please enter a URL', 'error');
        return;
    }

    const downloadBtn = document.getElementById('download-btn');
    downloadBtn.disabled = true;
    downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting...';

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url,
                quality,
                audio_only: audioOnly,
                is_playlist: isPlaylist,
                platform: platform !== 'auto' ? platform : undefined
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showNotification(`Download started: ${data.type}`, 'success');
            document.getElementById('url').value = '';
            loadDownloads();
        } else {
            showNotification(data.error || 'Download failed', 'error');
        }
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    } finally {
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = '<i class="fas fa-download"></i> Start Download';
    }
}

// Load Active Downloads
async function loadDownloads() {
    try {
        const response = await fetch('/api/downloads');
        const data = await response.json();

        const container = document.getElementById('downloads-container');

        if (data.downloads.length === 0) {
            container.innerHTML = '<p class="empty-state">No active downloads</p>';
            return;
        }

        container.innerHTML = data.downloads.map(task => createDownloadItem(task)).join('');
    } catch (error) {
        console.error('Error loading downloads:', error);
    }
}

// Create Download Item HTML
function createDownloadItem(task) {
    const statusClass = `status-${task.status}`;
    const itemClass = task.status === 'completed' ? 'completed' : 
                      task.status === 'failed' ? 'failed' : '';

    return `
        <div class="download-item ${itemClass}">
            <div class="download-header">
                <span class="download-url">${escapeHtml(task.url)}</span>
                <span class="download-type">${task.type}</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${task.progress}%"></div>
            </div>
            <div class="download-stats">
                <span class="download-stat ${statusClass}">
                    <i class="fas fa-circle-notch ${task.status === 'downloading' ? 'fa-spin' : ''}"></i>
                    ${capitalize(task.status)}
                </span>
                <span class="download-stat">
                    <i class="fas fa-tachometer-alt"></i> ${task.speed}
                </span>
                <span class="download-stat">
                    <i class="fas fa-clock"></i> ${task.eta}
                </span>
                <span class="download-stat">
                    <i class="fas fa-hdd"></i> ${task.downloaded} / ${task.total}
                </span>
                ${task.filename ? `
                <span class="download-stat">
                    <i class="fas fa-file"></i> ${escapeHtml(task.filename)}
                </span>
                ` : ''}
            </div>
            ${task.error ? `<p style="color: var(--danger-color); margin-top: 10px;">Error: ${escapeHtml(task.error)}</p>` : ''}
        </div>
    `;
}

// Clone Telegram Channel
async function cloneChannel() {
    const apiId = document.getElementById('tg-api-id').value.trim();
    const apiHash = document.getElementById('tg-api-hash').value.trim();
    const phone = document.getElementById('tg-phone').value.trim();
    const source = document.getElementById('tg-source').value.trim();
    const dest = document.getElementById('tg-dest').value.trim();
    const cloneType = document.getElementById('tg-clone-type').value;
    const limit = parseInt(document.getElementById('tg-limit').value);

    if (!apiId || !apiHash || !phone || !source || !dest) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }

    const cloneBtn = document.getElementById('clone-btn');
    cloneBtn.disabled = true;
    cloneBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cloning...';

    try {
        const response = await fetch('/api/telegram/clone', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                api_id: parseInt(apiId),
                api_hash: apiHash,
                phone,
                source,
                dest,
                clone_type: cloneType,
                limit
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showNotification(`Successfully cloned ${data.cloned_count} messages`, 'success');
        } else {
            showNotification(data.error || 'Clone failed', 'error');
        }
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    } finally {
        cloneBtn.disabled = false;
        cloneBtn.innerHTML = '<i class="fas fa-copy"></i> Clone Channel/Group';
    }
}

// Load Files
async function loadFiles() {
    try {
        const response = await fetch('/api/files');
        const data = await response.json();

        const container = document.getElementById('files-container');

        if (data.files.length === 0) {
            container.innerHTML = '<p class="empty-state">No files downloaded yet</p>';
            return;
        }

        container.innerHTML = data.files.map(file => `
            <div class="file-item">
                <div class="file-info">
                    <i class="fas fa-file-video file-icon"></i>
                    <div>
                        <div class="file-name">${escapeHtml(file.name)}</div>
                        <div class="file-meta">${formatSize(file.size)} • ${formatDate(file.modified)}</div>
                    </div>
                </div>
                <div class="file-actions">
                    <a href="/api/files/${encodeURIComponent(file.path)}" download>
                        <i class="fas fa-download"></i> Download
                    </a>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading files:', error);
    }
}

// Show Notification
function showNotification(message, type = 'info') {
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#6366f1'
    };

    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${colors[type]};
        color: white;
        padding: 16px 24px;
        border-radius: 10px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease;
        max-width: 400px;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Utility Functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Add animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
    }
`;
document.head.appendChild(style);

console.log('Universal Downloader Frontend loaded');
