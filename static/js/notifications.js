// Clean Toast Notifications System
(function() {
    'use strict';
    
    // Global state
    const state = {
        shownToasts: new Set(),
        lastPolledTime: Date.now(),
        notifications: [],
        unreadCount: 0
    };

    // Toast configuration
    const toastConfig = {
        autoClose: 5000,
        position: 'top-right'
    };

    // Simple notification sound function
    function playNotificationSound() {
        try {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = 0.3; // 30% volume - not too loud
            audio.play().catch(error => {
                // Silently handle any autoplay restrictions
                console.log('Note: Sound muted due to browser restrictions');
            });
        } catch (error) {
            // Silently handle any errors to not disrupt notifications
            console.log('Note: Unable to play notification sound');
        }
    }

    // Helper function: Format time ago
    function timeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        let interval = Math.floor(seconds / 31536000);
        
        if (interval > 1) return interval + ' years ago';
        interval = Math.floor(seconds / 2592000);
        if (interval > 1) return interval + ' months ago';
        interval = Math.floor(seconds / 86400);
        if (interval > 1) return interval + ' days ago';
        interval = Math.floor(seconds / 3600);
        if (interval > 1) return interval + ' hours ago';
        interval = Math.floor(seconds / 60);
        if (interval > 1) return interval + ' minutes ago';
        return Math.floor(seconds) + ' seconds ago';
    }

    // Show toast notification
    function showUpdateToast(update) {
        if (state.shownToasts.has(update.id)) {
            return;
        }

        // Create or get toast container
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container';
            document.body.appendChild(toastContainer);
        }

        const toastElement = document.createElement('div');
        toastElement.className = 'toast-notification';
        
        const message = `${update.name} posted a new update in ${update.process}`;
        
        toastElement.innerHTML = `
            <div class="toast-header">
                <strong>New Update</strong>
                <small>${timeAgo(new Date(update.timestamp))}</small>
                <button class="toast-close" aria-label="Close notification">×</button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        document.body.appendChild(toastElement);
        
        // Add animation class
        setTimeout(() => {
            toastElement.classList.add('show');
        }, 10);
        
        // Handle close button click
        const closeButton = toastElement.querySelector('.toast-close');
        closeButton.addEventListener('click', () => {
            toastElement.classList.remove('show');
            setTimeout(() => {
                if (document.body.contains(toastElement)) {
                    document.body.removeChild(toastElement);
                }
            }, 300);
        });

        // Play notification sound
        playNotificationSound();

        // Add to shown toasts
        state.shownToasts.add(update.id);

        // Add to notifications list
        addNotification({
            type: 'new_update',
            title: 'New Update',
            message: message,
            update_id: update.id,
            timestamp: update.timestamp,
            unread: true
        });
    }

    // Check for new updates
    async function checkForNewUpdates() {
        try {
            const response = await fetch('/api/recent-updates?' + new URLSearchParams({
                since: state.lastPolledTime
            }));
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            
            if (data.success && data.updates && data.updates.length > 0) {
                data.updates.forEach(update => {
                    showUpdateToast(update);
                });
            }
            
            state.lastPolledTime = Date.now();
        } catch (error) {
            console.error('Error checking for updates:', error);
        }
    }

    // Start polling
    function startPollingForUpdates() {
        console.log('🔄 Starting polling for new updates...');
        
        // Initial check
        checkForNewUpdates();

        // Set up polling interval (every 30 seconds)
        setInterval(checkForNewUpdates, 30000);

        console.log('✅ Polling started - checking every 30 seconds');
    }

    // Add notification
    function addNotification(notification) {
        state.notifications.unshift(notification);

        // Keep only last 50 notifications
        if (state.notifications.length > 50) {
            state.notifications = state.notifications.slice(0, 50);
        }

        if (notification.unread) {
            state.unreadCount++;
            updateUnreadCounter(state.unreadCount);
        }

        // Store in localStorage
        localStorage.setItem('notifications', JSON.stringify(state.notifications));
    }

    // Update unread counter
    function updateUnreadCounter(count) {
        const counter = document.getElementById('unread-counter');
        if (!counter) return;

        if (count > 0) {
            counter.textContent = count > 99 ? '99+' : count.toString();
            counter.style.display = 'flex';
        } else {
            counter.style.display = 'none';
        }
    }

    // Initialize when document is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startPollingForUpdates);
    } else {
        startPollingForUpdates();
    }

    // Make functions globally available
    window.notifications = {
        checkForUpdates: checkForNewUpdates,
        showToast: showUpdateToast,
        getUnreadCount: () => state.unreadCount,
        clearUnread: () => {
            state.unreadCount = 0;
            updateUnreadCounter(0);
        }
    };
})();
