/**
 * Network Status Indicator
 * 
 * This module provides a global network status indicator that shows the current
 * connection state and recent connectivity issues.
 * 
 * Features:
 * - Shows current online/offline status
 * - Tracks recent connection failures
 * - Provides visual indication of connectivity issues
 * - Auto-updates when connection state changes
 */

// Create a global network status manager
window.addEventListener('DOMContentLoaded', () => {
    // Create and initialize the network status manager
    window.networkStatus = new NetworkStatusManager();
    
    // Listen for retry events from fetchWithRetry utility
    document.addEventListener('fetchRetry', (e) => {
        if (window.networkStatus) {
            window.networkStatus.logEvent(
                `Retrying request to ${window.networkStatus.shortenUrl(e.detail.url)}: ${e.detail.error}`, 
                'warning'
            );
            window.networkStatus.retrying = true;
            window.networkStatus.updateIndicator();
        }
    });
});

class NetworkStatusManager {
    constructor(options = {}) {
        // Configuration options
        this.options = Object.assign({
            checkInterval: 60000, // Check every minute by default
            pingEndpoint: '/healthz', // Health check endpoint
            maxLogEntries: 10,      // Maximum number of log entries to keep
            pingTimeout: 5000,      // Ping timeout in ms
        }, options);
        
        // Status tracking
        this.online = navigator.onLine;
        this.retrying = false;
        this.lastCheck = null;
        this.consecutiveFailures = 0;
        this.failureCount = 0;
        this.logs = [];
        
        // Initialize the UI elements
        this.initializeIndicator();
        
        // Bind to browser online/offline events
        this.bindEvents();
        
        // Perform initial check
        this.checkConnection();
        
        // Set up regular checking
        this.checkInterval = setInterval(
            () => this.checkConnection(), 
            this.options.checkInterval
        );
    }
    
    initializeIndicator() {
        // Find the indicator element
        this.indicator = document.getElementById('network-status-indicator');
        
        if (!this.indicator) {
            console.error('Network status indicator element not found');
            return;
        }
        
        // Find the popup element
        this.popup = document.getElementById('network-status-details');
        
        if (!this.popup) {
            console.error('Network status popup element not found');
            return;
        }
        
        // Find the log entries container
        this.logContainer = this.popup.querySelector('.log-entries');
        
        if (!this.logContainer) {
            console.error('Log entries container not found');
            return;
        }
        
        // Setup toggle behavior for the indicator
        this.indicator.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent clicks from propagating
            this.popup.classList.toggle('active');
            
            // Close the popup when clicking outside
            if (this.popup.classList.contains('active')) {
                document.addEventListener('click', this.closePopupHandler = () => {
                    this.popup.classList.remove('active');
                    document.removeEventListener('click', this.closePopupHandler);
                });
            } else {
                document.removeEventListener('click', this.closePopupHandler);
            }
        });
        
        // Prevent clicks inside popup from closing it
        this.popup.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        
        // Initial update
        this.updateIndicator();
    }
    
    bindEvents() {
        // Listen for browser online event
        window.addEventListener('online', () => {
            this.online = true;
            this.retrying = false;
            this.consecutiveFailures = 0;
            this.logEvent('Browser went online', 'success');
            this.updateIndicator();
            
            // Check connection to confirm
            this.checkConnection();
        });
        
        // Listen for browser offline event
        window.addEventListener('offline', () => {
            this.online = false;
            this.retrying = false;
            this.consecutiveFailures = 0;
            this.failureCount++;
            this.logEvent('Browser went offline', 'error');
            this.updateIndicator();
        });
    }
    
    async checkConnection() {
        // Already know we're offline from the browser
        if (!navigator.onLine) {
            this.online = false;
            this.updateIndicator();
            return;
        }
        
        // Try to fetch the health check endpoint
        const startTime = Date.now();
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.options.pingTimeout);
            
            const response = await fetch(this.options.pingEndpoint, {
                signal: controller.signal,
                method: 'GET',
                cache: 'no-store'
            });
            
            clearTimeout(timeoutId);
            
            if (response.ok) {
                // Connection successful
                const pingTime = Date.now() - startTime;
                this.lastCheck = new Date();
                this.online = true;
                this.retrying = false;
                
                // Reset failure counters on success
                if (this.consecutiveFailures > 0) {
                    this.logEvent('Connection recovered', 'success');
                    this.consecutiveFailures = 0;
                }
                
                this.updateIndicator(pingTime);
            } else {
                // Server error
                this.online = false;
                this.consecutiveFailures++;
                this.failureCount++;
                this.logEvent(`Server error: ${response.status}`, 'error');
                this.updateIndicator();
            }
        } catch (error) {
            // Connection error
            this.lastCheck = new Date();
            this.online = false;
            this.consecutiveFailures++;
            this.failureCount++;
            
            let errorMessage = 'Connection failed';
            if (error.name === 'AbortError') {
                errorMessage = 'Connection timed out';
            } else if (error.message) {
                errorMessage = error.message;
            }
            
            this.logEvent(errorMessage, 'error');
            this.updateIndicator();
        }
    }
    
    updateIndicator(pingTime) {
        if (!this.indicator) return;
        
        // Remove all status classes
        this.indicator.classList.remove(
            'network-status-online',
            'network-status-offline',
            'network-status-warning',
            'network-status-retrying'
        );
        
        // Update status icon and text
        const statusIcon = this.indicator.querySelector('.status-icon');
        const statusText = this.indicator.querySelector('.status-text');
        
        // Update popup elements
        if (this.popup) {
            const statusBadge = this.popup.querySelector('.status-badge');
            const pingTimeElem = this.popup.querySelector('.ping-time');
            
            if (statusBadge) {
                statusBadge.textContent = this.online 
                    ? (this.retrying ? 'Reconnecting' : 'Online') 
                    : 'Offline';
                
                statusBadge.classList.remove('status-online', 'status-offline', 'status-warning');
                statusBadge.classList.add(this.online 
                    ? (this.retrying ? 'status-warning' : 'status-online') 
                    : 'status-offline');
            }
            
            if (pingTimeElem) {
                pingTimeElem.textContent = this.lastCheck 
                    ? `Last check: ${this.getRelativeTime(this.lastCheck)}${pingTime ? ` (${pingTime}ms)` : ''}`
                    : 'Never checked';
            }
        }
        
        if (this.online) {
            if (this.retrying) {
                // Attempting to reconnect
                this.indicator.classList.add('network-status-warning');
                if (statusIcon) statusIcon.textContent = '⚠️';
                if (statusText) statusText.textContent = 'Reconnecting';
            } else {
                // Fully online
                this.indicator.classList.add('network-status-online');
                if (statusIcon) statusIcon.textContent = '✓';
                if (statusText) statusText.textContent = 'Connected';
            }
        } else {
            // Offline
            this.indicator.classList.add('network-status-offline');
            if (statusIcon) statusIcon.textContent = '✗';
            if (statusText) statusText.textContent = 'Offline';
        }
    }
    
    logEvent(message, type = 'info') {
        // Create log entry
        const entry = {
            timestamp: new Date(),
            message,
            type
        };
        
        // Add to log
        this.logs.unshift(entry);
        
        // Limit log size
        if (this.logs.length > this.options.maxLogEntries) {
            this.logs.pop();
        }
        
        // Update UI if available
        if (this.logContainer) {
            // Clear existing logs
            while (this.logContainer.firstChild) {
                this.logContainer.removeChild(this.logContainer.firstChild);
            }
            
            // Add new logs
            this.logs.forEach(log => {
                const logElement = document.createElement('div');
                logElement.className = `log-entry log-${log.type}`;
                
                const timeElement = document.createElement('span');
                timeElement.className = 'log-time';
                timeElement.textContent = this.getRelativeTime(log.timestamp);
                
                const messageElement = document.createElement('span');
                messageElement.className = 'log-message';
                messageElement.textContent = log.message;
                
                logElement.appendChild(timeElement);
                logElement.appendChild(messageElement);
                
                this.logContainer.appendChild(logElement);
            });
        }
    }
    
    getRelativeTime(date) {
        const now = new Date();
        const diffSeconds = Math.floor((now - date) / 1000);
        
        if (diffSeconds < 5) {
            return 'Just now';
        } else if (diffSeconds < 60) {
            return `${diffSeconds} seconds ago`;
        } else if (diffSeconds < 3600) {
            const minutes = Math.floor(diffSeconds / 60);
            return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`;
        } else if (diffSeconds < 86400) {
            const hours = Math.floor(diffSeconds / 3600);
            return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`;
        } else {
            return date.toLocaleTimeString();
        }
    }
    
    shortenUrl(url) {
        if (!url) return '';
        
        // Get URL object
        try {
            const urlObj = new URL(url);
            // Return just the path
            return urlObj.pathname.length > 25 
                ? urlObj.pathname.substring(0, 22) + '...' 
                : urlObj.pathname;
        } catch (e) {
            // Not a valid URL, return a portion
            return url.length > 25 ? url.substring(0, 22) + '...' : url;
        }
    }
    
    checkNow() {
        // Force an immediate connection check
        this.checkConnection();
    }
    
    destroy() {
        // Clean up intervals
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
        }
        
        // Remove event listeners
        window.removeEventListener('online', this.handleOnline);
        window.removeEventListener('offline', this.handleOffline);
        
        // Clean up popup handler if active
        if (this.closePopupHandler) {
            document.removeEventListener('click', this.closePopupHandler);
        }
    }
}