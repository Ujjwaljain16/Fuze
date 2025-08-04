/**
 * API Key Manager - Frontend Component
 * Handles user API key management through web interface
 */

class APIKeyManager {
    constructor() {
        this.apiKeyInput = null;
        this.apiKeyStatus = null;
        this.usageStats = null;
        this.init();
    }

    init() {
        this.createAPIKeyModal();
        this.bindEvents();
        this.loadCurrentStatus();
    }

    createAPIKeyModal() {
        const modalHTML = `
            <div id="apiKeyModal" class="modal fade" tabindex="-1" role="dialog">
                <div class="modal-dialog modal-lg" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-key"></i> Manage Your API Key
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-8">
                                    <div class="mb-3">
                                        <label for="apiKeyInput" class="form-label">
                                            <strong>Gemini API Key</strong>
                                        </label>
                                        <div class="input-group">
                                            <input type="password" 
                                                   class="form-control" 
                                                   id="apiKeyInput" 
                                                   placeholder="AIzaSy... (Your Gemini API Key)"
                                                   maxlength="39">
                                            <button class="btn btn-outline-secondary" 
                                                    type="button" 
                                                    id="toggleApiKey">
                                                <i class="fas fa-eye"></i>
                                            </button>
                                        </div>
                                        <div class="form-text">
                                            <i class="fas fa-info-circle"></i>
                                            Get your free API key from 
                                            <a href="https://makersuite.google.com/app/apikey" target="_blank">
                                                Google AI Studio
                                            </a>
                                        </div>
                                    </div>
                                    
                                    <div class="mb-3">
                                        <label for="apiKeyName" class="form-label">
                                            <strong>API Key Name (Optional)</strong>
                                        </label>
                                        <input type="text" 
                                               class="form-control" 
                                               id="apiKeyName" 
                                               placeholder="My Personal Key">
                                        <div class="form-text">
                                            Give your API key a friendly name for easy identification
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="col-md-4">
                                    <div class="card">
                                        <div class="card-header">
                                            <h6 class="mb-0">
                                                <i class="fas fa-chart-line"></i> Usage Stats
                                            </h6>
                                        </div>
                                        <div class="card-body" id="usageStats">
                                            <div class="text-center">
                                                <div class="spinner-border spinner-border-sm" role="status">
                                                    <span class="visually-hidden">Loading...</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="alert alert-info">
                                <i class="fas fa-lightbulb"></i>
                                <strong>Why use your own API key?</strong>
                                <ul class="mb-0 mt-2">
                                    <li>No rate limit conflicts with other users</li>
                                    <li>You control your own API usage and costs</li>
                                    <li>Better performance and reliability</li>
                                    <li>Free tier: 15 requests/minute, 1500 requests/day</li>
                                </ul>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                Cancel
                            </button>
                            <button type="button" class="btn btn-primary" id="saveApiKey">
                                <i class="fas fa-save"></i> Save API Key
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page if it doesn't exist
        if (!document.getElementById('apiKeyModal')) {
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }
    }

    bindEvents() {
        // API Key toggle visibility
        document.addEventListener('click', (e) => {
            if (e.target.id === 'toggleApiKey') {
                this.toggleApiKeyVisibility();
            }
        });

        // Save API key
        document.addEventListener('click', (e) => {
            if (e.target.id === 'saveApiKey') {
                this.saveApiKey();
            }
        });

        // API Key input validation
        document.addEventListener('input', (e) => {
            if (e.target.id === 'apiKeyInput') {
                this.validateApiKey(e.target.value);
            }
        });
    }

    toggleApiKeyVisibility() {
        const input = document.getElementById('apiKeyInput');
        const toggleBtn = document.getElementById('toggleApiKey');
        const icon = toggleBtn.querySelector('i');
        
        if (input.type === 'password') {
            input.type = 'text';
            icon.className = 'fas fa-eye-slash';
        } else {
            input.type = 'password';
            icon.className = 'fas fa-eye';
        }
    }

    validateApiKey(apiKey) {
        const isValid = apiKey.startsWith('AIza') && apiKey.length >= 30;
        const input = document.getElementById('apiKeyInput');
        
        if (apiKey.length > 0) {
            if (isValid) {
                input.classList.remove('is-invalid');
                input.classList.add('is-valid');
            } else {
                input.classList.remove('is-valid');
                input.classList.add('is-invalid');
            }
        } else {
            input.classList.remove('is-valid', 'is-invalid');
        }
    }

    async saveApiKey() {
        const apiKey = document.getElementById('apiKeyInput').value.trim();
        const apiKeyName = document.getElementById('apiKeyName').value.trim() || 'My API Key';
        
        if (!apiKey) {
            this.showAlert('Please enter your API key', 'warning');
            return;
        }
        
        if (!apiKey.startsWith('AIza') || apiKey.length < 30) {
            this.showAlert('Please enter a valid Gemini API key', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/user/api-key', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    api_key: apiKey,
                    api_key_name: apiKeyName
                })
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showAlert('API key saved successfully!', 'success');
                this.loadCurrentStatus();
                this.updateUI();
            } else {
                this.showAlert(result.error || 'Failed to save API key', 'danger');
            }
        } catch (error) {
            console.error('Error saving API key:', error);
            this.showAlert('Failed to save API key. Please try again.', 'danger');
        }
    }

    async loadCurrentStatus() {
        try {
            const response = await fetch('/api/user/api-key/status', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (response.ok) {
                const status = await response.json();
                this.updateUsageStats(status);
            }
        } catch (error) {
            console.error('Error loading API key status:', error);
        }
    }

    updateUsageStats(status) {
        const statsContainer = document.getElementById('usageStats');
        
        if (!statsContainer) return;
        
        const hasApiKey = status.has_api_key;
        const apiKeyStatus = status.api_key_status;
        const requestsToday = status.requests_today || 0;
        const dailyLimit = status.daily_limit || 1500;
        const requestsThisMonth = status.requests_this_month || 0;
        const monthlyLimit = status.monthly_limit || 45000;
        const canMakeRequest = status.can_make_request;
        
        const usagePercentage = Math.round((requestsToday / dailyLimit) * 100);
        const monthlyUsagePercentage = Math.round((requestsThisMonth / monthlyLimit) * 100);
        
        statsContainer.innerHTML = `
            <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="text-muted">API Key Status</span>
                    <span class="badge ${hasApiKey ? 'bg-success' : 'bg-secondary'}">
                        ${hasApiKey ? 'Active' : 'Not Set'}
                    </span>
                </div>
                
                ${hasApiKey ? `
                    <div class="mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="text-muted">Daily Usage</span>
                            <span class="text-muted">${requestsToday}/${dailyLimit}</span>
                        </div>
                        <div class="progress" style="height: 8px;">
                            <div class="progress-bar ${usagePercentage > 80 ? 'bg-warning' : 'bg-success'}" 
                                 style="width: ${usagePercentage}%"></div>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="text-muted">Monthly Usage</span>
                            <span class="text-muted">${requestsThisMonth}/${monthlyLimit}</span>
                        </div>
                        <div class="progress" style="height: 8px;">
                            <div class="progress-bar ${monthlyUsagePercentage > 80 ? 'bg-warning' : 'bg-info'}" 
                                 style="width: ${monthlyUsagePercentage}%"></div>
                        </div>
                    </div>
                    
                    <div class="text-center">
                        <span class="badge ${canMakeRequest ? 'bg-success' : 'bg-warning'}">
                            ${canMakeRequest ? 'Ready' : 'Rate Limited'}
                        </span>
                    </div>
                ` : `
                    <div class="text-center text-muted">
                        <i class="fas fa-key fa-2x mb-2"></i>
                        <p class="mb-0">No API key set</p>
                    </div>
                `}
            </div>
        `;
    }

    updateUI() {
        // Update any UI elements that show API key status
        const apiKeyStatusElements = document.querySelectorAll('.api-key-status');
        apiKeyStatusElements.forEach(element => {
            this.loadCurrentStatus();
        });
    }

    showAlert(message, type = 'info') {
        // Create Bootstrap alert
        const alertHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Add to page
        const container = document.querySelector('.container') || document.body;
        container.insertAdjacentHTML('afterbegin', alertHTML);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = document.querySelector('.alert');
            if (alert) {
                alert.remove();
            }
        }, 5000);
    }

    getAuthToken() {
        // Get JWT token from localStorage or cookie
        return localStorage.getItem('authToken') || this.getCookie('authToken');
    }

    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    // Public method to open the modal
    openModal() {
        const modal = new bootstrap.Modal(document.getElementById('apiKeyModal'));
        modal.show();
    }
}

// Initialize API Key Manager
document.addEventListener('DOMContentLoaded', () => {
    window.apiKeyManager = new APIKeyManager();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIKeyManager;
} 