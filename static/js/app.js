// Video Processing Dashboard JavaScript

// Global variables
let socket;
let isConnected = false;

// Initialize dashboard
function initializeDashboard() {
    initializeWebSocket();
    setupEventListeners();
    startPeriodicUpdates();
}

// Initialize WebSocket connection
function initializeWebSocket() {
    socket = io();
    
    socket.on('connect', function() {
        isConnected = true;
        console.log('Connected to server');
        showToast('Connected to server', 'success');
    });
    
    socket.on('disconnect', function() {
        isConnected = false;
        console.log('Disconnected from server');
        showToast('Disconnected from server', 'warning');
    });
    
    socket.on('status_update', function(data) {
        updateMovieStatus(data);
    });
    
    socket.on('new_movie', function(data) {
        addNewMovieRow(data);
        updateStatistics();
    });
    
    socket.on('error', function(error) {
        console.error('Socket error:', error);
        showToast('Connection error: ' + error, 'danger');
    });
}

// Setup event listeners
function setupEventListeners() {
    // Refresh button
    document.addEventListener('click', function(e) {
        if (e.target.closest('[onclick*="refreshDashboard"]')) {
            e.preventDefault();
            refreshDashboard();
        }
    });
}

// Start periodic updates
function startPeriodicUpdates() {
    // Update statistics every 30 seconds
    setInterval(updateStatistics, 30000);
    
    // Check connection status every 10 seconds
    setInterval(checkConnectionStatus, 10000);
}

// API Functions
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        showToast('API call failed: ' + error.message, 'danger');
        throw error;
    }
}

// Movie Management Functions
async function startConversion(movieId) {
    const button = document.getElementById(`convert-btn-${movieId}`);
    if (button) {
        button.classList.add('btn-loading');
        button.disabled = true;
    }
    
    try {
        const result = await apiCall(`/api/convert/${movieId}`, {
            method: 'POST'
        });
        
        if (result.success) {
            showToast(result.message, 'success');
            updateMovieRow(movieId);
        } else {
            showToast(result.error || 'Conversion failed', 'danger');
        }
    } catch (error) {
        showToast('Failed to start conversion', 'danger');
    } finally {
        if (button) {
            button.classList.remove('btn-loading');
            button.disabled = false;
        }
    }
}

async function cancelConversion(movieId) {
    const button = document.getElementById(`cancel-btn-${movieId}`);
    if (button) {
        button.classList.add('btn-loading');
        button.disabled = true;
    }
    
    try {
        const result = await apiCall(`/api/cancel/${movieId}`, {
            method: 'POST'
        });
        
        if (result.success) {
            showToast(result.message, 'success');
            updateMovieRow(movieId);
        } else {
            showToast(result.error || 'Cancellation failed', 'danger');
        }
    } catch (error) {
        showToast('Failed to cancel conversion', 'danger');
    } finally {
        if (button) {
            button.classList.remove('btn-loading');
            button.disabled = false;
        }
    }
}

async function deleteMovie(movieId) {
    if (!confirm('Are you sure you want to delete this movie and all its files?')) {
        return;
    }
    
    const button = document.getElementById(`delete-btn-${movieId}`);
    if (button) {
        button.classList.add('btn-loading');
        button.disabled = true;
    }
    
    try {
        const result = await apiCall(`/api/delete/${movieId}`, {
            method: 'DELETE'
        });
        
        if (result.success) {
            showToast(result.message, 'success');
            removeMovieRow(movieId);
            updateStatistics();
        } else {
            showToast(result.error || 'Deletion failed', 'danger');
        }
    } catch (error) {
        showToast('Failed to delete movie', 'danger');
    } finally {
        if (button) {
            button.classList.remove('btn-loading');
            button.disabled = false;
        }
    }
}

function viewFiles(movieId) {
    // Open file explorer to OUTPUT folder (Windows specific)
    const outputPath = `OUTPUT/${movieId}`;
    showToast(`Files are located in: ${outputPath}`, 'info');
    
    // You could implement a file browser modal here
    // or provide download links for the HLS files
}

async function scanFolder() {
    try {
        const result = await apiCall('/api/scan', {
            method: 'POST'
        });
        
        if (result.success) {
            showToast(result.message, 'success');
            // Refresh the page after a short delay to show new movies
            setTimeout(() => {
                refreshDashboard();
            }, 2000);
        } else {
            showToast(result.error || 'Scan failed', 'danger');
        }
    } catch (error) {
        showToast('Failed to scan folder', 'danger');
    }
}

// UI Update Functions
function updateMovieStatus(data) {
    const movieId = data.movie_id;
    const status = data.status;
    const progress = data.progress || 0;
    
    // Update progress bar
    const progressBar = document.getElementById(`progress-${movieId}`);
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
        progressBar.textContent = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
        
        // Add animation for active progress
        if (status === 'IN_PROGRESS') {
            progressBar.classList.add('progress-bar-animated');
        } else {
            progressBar.classList.remove('progress-bar-animated');
        }
    }
    
    // Update status badge
    const statusBadge = document.getElementById(`status-${movieId}`);
    if (statusBadge) {
        const statusConfig = getStatusConfig(status);
        statusBadge.className = `badge bg-${statusConfig.color}`;
        statusBadge.textContent = `${statusConfig.icon} ${status}`;
    }
    
    // Update action buttons
    updateActionButtons(movieId, status);
    
    // Highlight row temporarily
    const row = document.getElementById(`movie-row-${movieId}`);
    if (row) {
        row.classList.add('movie-row-updated');
        setTimeout(() => {
            row.classList.remove('movie-row-updated');
        }, 2000);
    }
    
    // Update statistics
    updateStatistics();
}

function updateActionButtons(movieId, status) {
    const actionsCell = document.querySelector(`#movie-row-${movieId} td:last-child`);
    if (!actionsCell) return;
    
    let buttonsHtml = '<div class="btn-group btn-group-sm" role="group">';
    
    if (status === 'NEW' || status === 'ERROR') {
        buttonsHtml += `
            <button class="btn btn-success" onclick="startConversion('${movieId}')" id="convert-btn-${movieId}">
                <i class="bi bi-play-circle"></i> Convert
            </button>
        `;
    } else if (status === 'QUEUED') {
        buttonsHtml += `
            <button class="btn btn-warning" onclick="cancelConversion('${movieId}')" id="cancel-btn-${movieId}">
                <i class="bi bi-x-circle"></i> Cancel
            </button>
        `;
    } else if (status === 'DONE') {
        buttonsHtml += `
            <button class="btn btn-info" onclick="viewFiles('${movieId}')" id="view-btn-${movieId}">
                <i class="bi bi-folder2-open"></i> View Files
            </button>
        `;
    }
    
    if (status !== 'IN_PROGRESS') {
        buttonsHtml += `
            <button class="btn btn-danger" onclick="deleteMovie('${movieId}')" id="delete-btn-${movieId}">
                <i class="bi bi-trash"></i>
            </button>
        `;
    }
    
    buttonsHtml += '</div>';
    actionsCell.innerHTML = buttonsHtml;
}

function getStatusConfig(status) {
    const configs = {
        'NEW': { color: 'warning', icon: '🟡' },
        'QUEUED': { color: 'info', icon: '🔵' },
        'IN_PROGRESS': { color: 'danger', icon: '🔴' },
        'DONE': { color: 'success', icon: '🟢' },
        'ERROR': { color: 'dark', icon: '⚫' }
    };
    return configs[status] || { color: 'secondary', icon: '⚪' };
}

async function updateMovieRow(movieId) {
    try {
        const movie = await apiCall(`/api/movies/${movieId}`);
        // Update the specific row with new data
        // This is a simplified version - you might want to rebuild the entire row
        updateMovieStatus({
            movie_id: movieId,
            status: movie.status,
            progress: movie.overall_progress
        });
    } catch (error) {
        console.error('Failed to update movie row:', error);
    }
}

function addNewMovieRow(movie) {
    const tableBody = document.getElementById('movies-table-body');
    if (!tableBody) return;
    
    // Create new row HTML
    const rowHtml = createMovieRowHtml(movie);
    
    // Insert at the beginning of the table
    tableBody.insertAdjacentHTML('afterbegin', rowHtml);
    
    // Highlight the new row
    const newRow = document.getElementById(`movie-row-${movie.id}`);
    if (newRow) {
        newRow.classList.add('movie-row-updated');
        setTimeout(() => {
            newRow.classList.remove('movie-row-updated');
        }, 3000);
    }
}

function createMovieRowHtml(movie) {
    const statusConfig = getStatusConfig(movie.status);
    const fileSizeFormatted = formatFileSize(movie.file_size);
    const targetQualities = movie.target_qualities ? movie.target_qualities.join(', ') : '';
    
    return `
        <tr id="movie-row-${movie.id}" data-movie-id="${movie.id}">
            <td><code class="text-primary">${movie.id}</code></td>
            <td>
                <div class="d-flex align-items-center">
                    <i class="bi bi-file-earmark-play me-2"></i>
                    <span title="${movie.filename}">
                        ${movie.filename.length > 30 ? movie.filename.substring(0, 30) + '...' : movie.filename}
                    </span>
                </div>
            </td>
            <td>${fileSizeFormatted}</td>
            <td>
                ${movie.source_resolution ? 
                    `<span class="badge bg-info">${movie.source_resolution}</span>` : 
                    '<span class="text-muted">Unknown</span>'
                }
            </td>
            <td><small class="text-muted">${targetQualities}</small></td>
            <td>
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar progress-bar-striped" 
                         id="progress-${movie.id}"
                         role="progressbar" 
                         style="width: ${movie.overall_progress || 0}%"
                         aria-valuenow="${movie.overall_progress || 0}" 
                         aria-valuemin="0" 
                         aria-valuemax="100">
                        ${movie.overall_progress || 0}%
                    </div>
                </div>
            </td>
            <td>
                <span class="badge bg-${statusConfig.color}" id="status-${movie.id}">
                    ${statusConfig.icon} ${movie.status}
                </span>
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    ${movie.status === 'NEW' || movie.status === 'ERROR' ? 
                        `<button class="btn btn-success" onclick="startConversion('${movie.id}')" id="convert-btn-${movie.id}">
                            <i class="bi bi-play-circle"></i> Convert
                        </button>` : ''
                    }
                    ${movie.status !== 'IN_PROGRESS' ? 
                        `<button class="btn btn-danger" onclick="deleteMovie('${movie.id}')" id="delete-btn-${movie.id}">
                            <i class="bi bi-trash"></i>
                        </button>` : ''
                    }
                </div>
            </td>
        </tr>
    `;
}

function removeMovieRow(movieId) {
    const row = document.getElementById(`movie-row-${movieId}`);
    if (row) {
        row.remove();
    }
}

async function updateStatistics() {
    try {
        const stats = await apiCall('/api/stats');
        
        // Update statistics cards
        const totalMoviesEl = document.getElementById('total-movies');
        const completedMoviesEl = document.getElementById('completed-movies');
        const queueLengthEl = document.getElementById('queue-length');
        const inProgressEl = document.getElementById('in-progress');
        
        if (totalMoviesEl) totalMoviesEl.textContent = stats.total_movies;
        if (completedMoviesEl) completedMoviesEl.textContent = stats.completed_movies;
        if (queueLengthEl) queueLengthEl.textContent = stats.queued;
        if (inProgressEl) inProgressEl.textContent = stats.in_progress;
        
    } catch (error) {
        console.error('Failed to update statistics:', error);
    }
}

// Utility Functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0B';
    
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    
    return (bytes / Math.pow(1024, i)).toFixed(1) + sizes[i];
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastBody = document.getElementById('toast-body');
    
    if (!toast || !toastBody) return;
    
    // Set toast type
    toast.className = `toast border-${type}`;
    toastBody.textContent = message;
    
    // Show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

function refreshDashboard() {
    location.reload();
}

function checkConnectionStatus() {
    if (!isConnected && socket) {
        socket.connect();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});
