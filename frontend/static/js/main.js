/**
 * Agente de Inteligência Geopolítica - Main JavaScript
 */

// API Status Check
document.addEventListener('DOMContentLoaded', function() {
    checkApiStatus();
    // Check status every 30 seconds
    setInterval(checkApiStatus, 30000);
});

/**
 * Check API status and update badge
 */
async function checkApiStatus() {
    const statusBadge = document.getElementById('api-status');
    if (!statusBadge) return;

    try {
        const response = await fetch('/api/status', { timeout: 5000 });
        const data = await response.json();

        if (data.online) {
            statusBadge.className = 'badge bg-success me-2';
            statusBadge.innerHTML = '<i class="bi bi-circle-fill me-1"></i> API Online';
        } else {
            statusBadge.className = 'badge bg-danger me-2';
            statusBadge.innerHTML = '<i class="bi bi-circle-fill me-1"></i> API Offline';
        }
    } catch (error) {
        statusBadge.className = 'badge bg-danger me-2';
        statusBadge.innerHTML = '<i class="bi bi-circle-fill me-1"></i> API Offline';
    }
}

/**
 * Show loading indicator
 */
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.remove('d-none');
    }
}

/**
 * Hide loading indicator
 */
function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.add('d-none');
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }

    // Create toast
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type}" role="alert">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHtml);

    // Show toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();

    // Remove toast after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

/**
 * Format date to local string
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Get score color class
 */
function getScoreColor(score) {
    if (score >= 70) return 'success';
    if (score >= 50) return 'warning';
    return 'danger';
}

/**
 * Get score label
 */
function getScoreLabel(score) {
    if (score >= 85) return 'Muito Alta';
    if (score >= 70) return 'Alta';
    if (score >= 50) return 'Média';
    if (score >= 30) return 'Baixa';
    return 'Muito Baixa';
}

/**
 * Truncate text with ellipsis
 */
function truncateText(text, maxLength = 200) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength).trim() + '...';
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copiado para a área de transferência!', 'success');
    } catch (err) {
        showToast('Erro ao copiar', 'danger');
    }
}

/**
 * Download text as file
 */
function downloadTextFile(content, filename) {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

/**
 * AJAX Search
 */
async function searchTopicAjax(topic, maxArticles = 5) {
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                topic: topic,
                max_articles_per_source: maxArticles
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Search error:', error);
        throw error;
    }
}

/**
 * AJAX Generate Report
 */
async function generateReportAjax(topic, minSources = 3, includeScenarios = true) {
    try {
        const response = await fetch('/api/report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                topic: topic,
                min_sources: minSources,
                include_scenarios: includeScenarios
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Report error:', error);
        throw error;
    }
}

/**
 * Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for use in templates
window.GeopoliticalApp = {
    checkApiStatus,
    showLoading,
    hideLoading,
    showToast,
    formatDate,
    getScoreColor,
    getScoreLabel,
    truncateText,
    copyToClipboard,
    downloadTextFile,
    searchTopicAjax,
    generateReportAjax,
    debounce
};
