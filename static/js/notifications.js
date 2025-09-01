// Clean Toast Notifications System
let socket;
let notifications = [];
let unreadCount = 0;
let shownToasts = new Set(); // Track shown toasts to prevent duplicates

// Connection error handling variables (declared at top to avoid hoisting issues)
let connectionErrorToast = null;
let connectionErrorCount = 0;
let lastConnectionErrorTime = 0;

// Performance optimization: Debounce function
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

// Initialize Socket.IO connection for toast notifications
function initializeSocketIO() {
    console.log('🔌 Initializing Socket.IO for toast notifications...');

    if (typeof io !== 'undefined') {
        console.log('✅ Socket.IO library available');

        // Get the current host
        const protocol = window.location.protocol;
        const host = window.location.host;
        const socketUrl = `${protocol}//${host}`;

        console.log('🔗 Connecting to:', socketUrl);

        // Detect Vercel environment
        const isVercel = host.includes('vercel.app') ||
                        host.includes('now.sh') ||
                        window.location.hostname.includes('vercel') ||
                        document.querySelector('meta[name="generator"][content*="Vercel"]') !== null;

        console.log('🌐 Environment detected:', isVercel ? 'Vercel' : 'Other');

        // Vercel-optimized configuration for toast notifications
        const socketConfig = {
            timeout: 15000,  // Match server timeout
            forceNew: true,  // Force new connection
            reconnection: true,
            reconnectionAttempts: 3,  // Limited attempts for serverless
            reconnectionDelay: 2000,  // Delay between attempts
            reconnectionDelayMax: 5000,
            randomizationFactor: 0.5,
            secure: window.location.protocol === 'https:',
            rejectUnauthorized: false,
            path: '/socket.io',
            transports: ['polling'],  // Force polling only
            allowUpgrades: false,  // Disable upgrades
            cookie: false,  // Disable cookies
            // Serverless-specific settings
            autoConnect: true,
            closeOnBeforeunload: false,
            retries: 2,
            // Performance optimizations
            perMessageDeflate: false,  // Disable compression
            httpCompression: false,
            forceBase64: false,
            // Connection stability
            pingTimeout: 30000,  // Match server ping timeout
            pingInterval: 20000,  // Match server ping interval
            upgrade: false,  // Disable upgrade attempts
            rememberUpgrade: false,
            // Additional stability settings
            extraHeaders: {
                'Cache-Control': 'no-cache',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };

        // Vercel-specific adjustments
        if (isVercel) {
            socketConfig.pingTimeout = 30000;
            socketConfig.pingInterval = 20000;
            socketConfig.forceBase64 = true;  // Force base64 for Vercel
            socketConfig.timestampRequests = true;
            socketConfig.timestampParam = 't';
            console.log('⚡ Using Vercel-optimized Socket.IO settings');
        }

        socket = io(socketUrl, socketConfig);
        console.log('🔧 Socket.IO connection configured for serverless environment');

        // Attach event handlers
        attachSocketEventHandlers();
    } else {
        console.error('❌ Socket.IO library not available');
    }
}

// Initialize toast notification system
function initializeToastNotifications() {
    console.log('🍞 Initializing toast notification system...');

    try {
        // Initialize Socket.IO for toast notifications
        initializeSocketIO();

        // Load existing notifications from localStorage
        loadNotificationsFromStorage();

        // Update UI
        updateUnreadCounterEnhanced(unreadCount);

        console.log('✅ Toast notification system initialized successfully');
    } catch (error) {
        console.error('❌ Failed to initialize toast notification system:', error);
        // Fallback: Initialize without Socket.IO
        initializeFallbackMode();
    }
}

// Fallback mode when Socket.IO fails completely
function initializeFallbackMode() {
    console.log('🔄 Initializing fallback mode without Socket.IO...');

    // Load existing notifications from localStorage
    loadNotificationsFromStorage();

    // Update UI
    updateUnreadCounterEnhanced(unreadCount);

    // Set up periodic polling as fallback (less frequent)
    setInterval(() => {
        checkForNewUpdatesFallback();
    }, 300000); // Check every 5 minutes instead of every 30 seconds

    console.log('✅ Fallback mode initialized - using periodic polling');
}

// Fallback function to check for new updates when Socket.IO is unavailable
function checkForNewUpdatesFallback() {
    fetch('/api/recent-updates')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.updates && data.updates.length > 0) {
                // Check if we have any new updates we haven't shown
                const latestUpdate = data.updates[0];
                const lastShownUpdateId = localStorage.getItem('lastShownUpdateId');

                if (!lastShownUpdateId || latestUpdate.id !== lastShownUpdateId) {
                    // Show toast for the latest update
                    showUpdateToast({
                        id: latestUpdate.id,
                        name: latestUpdate.name,
                        process: latestUpdate.process,
                        timestamp: latestUpdate.timestamp
                    });

                    // Store the ID to prevent duplicate toasts
                    localStorage.setItem('lastShownUpdateId', latestUpdate.id);
                }
            }
        })
        .catch(error => {
            console.log('Fallback polling failed:', error);
        });
}

// Add a new notification
function addNotification(notification) {
    notifications.unshift(notification);

    // Keep only last 50 notifications
    if (notifications.length > 50) {
        notifications = notifications.slice(0, 50);
    }

    // Update unread count
    if (notification.unread) {
        unreadCount++;
        updateUnreadCounterEnhanced(unreadCount);
    }

    // Update notifications panel
    updateNotificationsPanel();

    // Store in localStorage
    localStorage.setItem('notifications', JSON.stringify(notifications));
}


// Show toast notification for new update
function showUpdateToast(update) {
    // Prevent duplicate toasts for the same update
    if (shownToasts.has(update.id)) {
        console.log('Toast already shown for update:', update.id);
        return;
    }

    const userName = update.name || 'Unknown User';
    const processInfo = update.process ? ` in **${update.process}** process` : '';
    const message = `New update posted by **${userName}**${processInfo}`;

    showToast(message, 'permanent', update.id);

    // Play notification sound
    console.log('🔊 Playing notification sound for new update...');
    playNotificationSound();

    // Mark this update as shown
    shownToasts.add(update.id);

    // Add to notifications list
    addNotification({
        type: 'new_update',
        title: 'New Update',
        message: `New update from ${userName}${processInfo}`,
        update_id: update.id,
        timestamp: update.timestamp,
        unread: true
    });
}

// Update the unread counter display
function updateUnreadCounter(count) {
    unreadCount = count;
    const counter = document.getElementById('unread-counter');

    if (counter) {
        if (count > 0) {
            counter.textContent = count > 99 ? '99+' : count.toString();
            counter.style.display = 'flex';
        } else {
            counter.style.display = 'none';
        }
    }
}

// Check for recent updates and show badge
function checkForRecentUpdatesAndShowBadge() {
    fetch('/api/latest-update-time')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.latest_timestamp) {
                const latestTime = new Date(data.latest_timestamp);
                const now = new Date();
                const diffHours = (now - latestTime) / (1000 * 60 * 60);

                const counter = document.getElementById('unread-counter');

                if (counter) {
                    if (diffHours <= 24) {
                        // Show red dot for recent updates (within 24 hours)
                        counter.textContent = '•';
                        counter.style.display = 'flex';
                        counter.style.fontSize = '20px';
                        counter.style.lineHeight = '1';
                        counter.classList.add('recent-update-badge');
                    } else if (unreadCount === 0) {
                        // Hide badge if no recent updates and no unread notifications
                        counter.style.display = 'none';
                        counter.classList.remove('recent-update-badge');
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error checking for recent updates:', error);
        });
}

// Enhanced updateUnreadCounter to work with recent updates badge
function updateUnreadCounterEnhanced(count) {
    unreadCount = count;
    const counter = document.getElementById('unread-counter');

    if (counter) {
        if (count > 0) {
            // Show notification count
            counter.textContent = count > 99 ? '99+' : count.toString();
            counter.style.display = 'flex';
            counter.style.fontSize = '11px';
            counter.style.lineHeight = 'normal';
            counter.classList.remove('recent-update-badge');
        } else {
            // Check for recent updates when no unread notifications
            checkForRecentUpdatesAndShowBadge();
        }
    }
}

// Update the notifications panel
function updateNotificationsPanel() {
    const notificationsList = document.getElementById('notifications-list');
    if (!notificationsList) return;
    
    notificationsList.innerHTML = '';
    
    if (notifications.length === 0) {
        notificationsList.innerHTML = '<div class="notification-item"><em>No notifications yet</em></div>';
        return;
    }
    
    notifications.forEach((notification, index) => {
        const notificationElement = createNotificationElement(notification, index);
        notificationsList.appendChild(notificationElement);
    });
}

// Create a notification element with optimized event handling
function createNotificationElement(notification, index) {
    const div = document.createElement('div');
    div.className = `notification-item ${notification.unread ? 'unread' : ''}`;
    
    // Use data attributes for better performance
    div.dataset.notificationId = notification.id;
    div.dataset.notificationIndex = index;
    
    // Format time with optimization for performance
    const time = formatNotificationTime(notification.timestamp);
    
    // Use DocumentFragment for better performance
    const fragment = document.createDocumentFragment();
    
    const title = document.createElement('div');
    title.className = 'notification-title';
    title.textContent = notification.title;
    fragment.appendChild(title);
    
    const message = document.createElement('div');
    message.className = 'notification-message';
    message.textContent = notification.message;
    fragment.appendChild(message);
    
    const timeEl = document.createElement('div');
    timeEl.className = 'notification-time';
    timeEl.textContent = time;
    fragment.appendChild(timeEl);
    
    div.appendChild(fragment);
    
    // Add touch feedback
    div.addEventListener('touchstart', () => {
        div.classList.add('touched');
    }, { passive: true });
    
    div.addEventListener('touchend', () => {
        div.classList.remove('touched');
    }, { passive: true });
    
    return div;
}

// Optimize time formatting
function formatNotificationTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    return date.toLocaleDateString();
}

// Handle notification click with debouncing and event delegation
function handleNotificationClick(event) {
    const item = event.target.closest('.notification-item');
    if (!item) return;
    
    const index = parseInt(item.dataset.notificationIndex, 10);
    const notification = notifications[index];
    if (!notification) return;
    // Mark as read
    if (notification.unread) {
        notification.unread = false;
        unreadCount = Math.max(0, unreadCount - 1);
        updateUnreadCounterEnhanced(unreadCount);
        updateNotificationsPanel();
        
        // If it's an update, mark it as read on the server
        if (notification.update_id && socket) {
            socket.emit('mark_as_read', { update_id: notification.update_id });
        }
        
        // Store updated notifications
        localStorage.setItem('notifications', JSON.stringify(notifications));
    }
    
    // Handle navigation if needed
    if (notification.type === 'new_update' && notification.update_id) {
        // Could navigate to the update or scroll to it
        console.log('Navigate to update:', notification.update_id);
    }
}

// Toggle notifications panel
function toggleNotifications() {
    const panel = document.getElementById('notifications-panel');
    if (panel) {
        const isVisible = panel.classList.contains('show');

        if (isVisible) {
            panel.classList.remove('show');
        } else {
            panel.classList.add('show');
            // Load notifications from localStorage
            loadNotificationsFromStorage();
            updateNotificationsPanel();
        }
    }
}

// Mark all notifications as read
function markAllAsRead() {
    notifications.forEach(notification => {
        notification.unread = false;
    });
    
    unreadCount = 0;
    updateUnreadCounterEnhanced(unreadCount);
    updateNotificationsPanel();
    
    // Store updated notifications
    localStorage.setItem('notifications', JSON.stringify(notifications));
}

// Load notifications from localStorage
function loadNotificationsFromStorage() {
    try {
        const stored = localStorage.getItem('notifications');
        if (stored) {
            notifications = JSON.parse(stored);
            // Count unread notifications
            unreadCount = notifications.filter(n => n.unread).length;
            updateUnreadCounterEnhanced(unreadCount);
        }
    } catch (error) {
        console.error('Error loading notifications from storage:', error);
        notifications = [];
        unreadCount = 0;
    }
}

// Play notification sound
function playNotificationSound() {
    // Check if user has enabled sound notifications (default to true)
    const soundEnabled = localStorage.getItem('notificationSoundEnabled') !== 'false';
    console.log('🔊 Sound enabled:', soundEnabled);

    if (!soundEnabled) {
        console.log('🔇 Sound notifications disabled by user');
        return;
    }

    try {
        console.log('🎵 Attempting to play notification sound...');
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.volume = 0.5; // Set volume to 50%

        // Add error handling for audio loading
        audio.addEventListener('error', function(e) {
            console.error('❌ Error loading notification sound:', e);
        });

        // Add success handler
        audio.addEventListener('canplaythrough', function() {
            console.log('✅ Notification sound loaded successfully');
        });

        audio.play().then(() => {
            console.log('🎵 Notification sound played successfully');
        }).catch(error => {
            console.error('❌ Could not play notification sound:', error);
            // Fallback: try to create a simple beep sound
            try {
                console.log('🔄 Attempting fallback beep sound...');
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();

                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);

                oscillator.frequency.value = 800;
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);

                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.3);
                console.log('✅ Fallback beep sound played');
            } catch (fallbackError) {
                console.error('❌ Fallback sound also failed:', fallbackError);
            }
        });
    } catch (error) {
        console.error('❌ Error creating notification sound:', error);
    }
}

// Show toast message
function showToast(message, duration = 6000, updateId = null) {
    const toast = document.createElement('div');
    toast.className = 'toast';

    // Support for bold text using **text** syntax
    const formattedMessage = message.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Create toast content container
    const toastContent = document.createElement('div');
    toastContent.className = 'toast-content';
    toastContent.innerHTML = formattedMessage;

    // Create close button for permanent notifications
    const isPermanent = duration === 'permanent';
    if (isPermanent) {
        toast.classList.add('toast-permanent');

        const closeButton = document.createElement('button');
        closeButton.className = 'toast-close';
        closeButton.innerHTML = '×';
        closeButton.setAttribute('aria-label', 'Close notification');
        closeButton.onclick = function() {
            closeToast(toast);
        };

        toast.appendChild(toastContent);
        toast.appendChild(closeButton);
    } else {
        toast.innerHTML = formattedMessage;
    }

    document.body.appendChild(toast);

    // Add unique ID to prevent conflicts, include update ID if provided
    const baseId = updateId ? `update-${updateId}` : `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    toast.id = baseId;

    setTimeout(() => {
        toast.classList.add('show');
    }, 100);

    // Auto-close only for non-permanent notifications
    if (!isPermanent) {
        setTimeout(() => {
            closeToast(toast);
        }, duration);
    }

    return toast; // Return the toast for tracking
}

// Close toast function
function closeToast(toast) {
    // Remove from shown toasts if it was a permanent update toast
    if (toast.classList.contains('toast-permanent')) {
        // Find the update ID from the toast ID
        const toastId = toast.id;
        if (toastId && toastId.startsWith('update-')) {
            const updateId = toastId.substring(7); // Remove 'update-' prefix
            if (updateId) {
                shownToasts.delete(updateId);
                console.log('Removed update from shown toasts:', updateId);
            }
        }
    }

    toast.classList.remove('show');
    setTimeout(() => {
        if (document.body.contains(toast)) {
            document.body.removeChild(toast);
        }
    }, 500);
}

// Close notifications panel when clicking outside
document.addEventListener('click', function(event) {
    const panel = document.getElementById('notifications-panel');
    const bell = document.getElementById('notification-bell');

    if (panel && bell && !panel.contains(event.target) && !bell.contains(event.target)) {
        panel.classList.remove('show');
    }
});

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Load existing notifications
    loadNotificationsFromStorage();

    // Initialize toast notification system
    initializeToastNotifications();

    // Update unread counter display
    updateUnreadCounterEnhanced(unreadCount);

    // Check for recent updates and show badge periodically - optimized
    checkForRecentUpdatesAndShowBadge();
    setInterval(checkForRecentUpdatesAndShowBadge, 600000); // Check every 10 minutes to reduce server load

    // Update notifications panel
    updateNotificationsPanel();

    // Initialize sound toggle state
    initializeSoundToggle();
});

// Toggle notification sound
function toggleNotificationSound() {
    const soundEnabled = localStorage.getItem('notificationSoundEnabled') !== 'false';
    const newState = !soundEnabled;

    localStorage.setItem('notificationSoundEnabled', newState.toString());

    // Update UI
    const soundToggle = document.getElementById('soundToggle');
    const soundIcon = document.getElementById('soundIcon');

    if (soundToggle && soundIcon) {
        if (newState) {
            soundToggle.classList.remove('disabled');
            soundIcon.className = 'fas fa-volume-up';
            soundToggle.title = 'Disable notification sounds';
        } else {
            soundToggle.classList.add('disabled');
            soundIcon.className = 'fas fa-volume-mute';
            soundToggle.title = 'Enable notification sounds';
        }
    }

    // Play a test sound if enabling
    if (newState) {
        playNotificationSound();
    }
}

// Initialize sound toggle state
function initializeSoundToggle() {
    // Set default to true if not already set
    if (localStorage.getItem('notificationSoundEnabled') === null) {
        localStorage.setItem('notificationSoundEnabled', 'true');
        console.log('🔊 Sound notifications enabled by default for new user');
    }

    const soundEnabled = localStorage.getItem('notificationSoundEnabled') !== 'false';
    const soundToggle = document.getElementById('soundToggle');
    const soundIcon = document.getElementById('soundIcon');

    if (soundToggle && soundIcon) {
        if (soundEnabled) {
            soundToggle.classList.remove('disabled');
            soundIcon.className = 'fas fa-volume-up';
            soundToggle.title = 'Disable notification sounds';
        } else {
            soundToggle.classList.add('disabled');
            soundIcon.className = 'fas fa-volume-mute';
            soundToggle.title = 'Enable notification sounds';
        }
    }
}




// Attach Socket.IO event handlers for toast notifications
function attachSocketEventHandlers() {
    socket.on('connect', function() {
        console.log('✅ Connected to Socket.IO for toast notifications');
        console.log('🔗 Socket ID:', socket.id);
        console.log('🌐 Transport:', socket.io.engine.transport ? socket.io.engine.transport.name : 'unknown');

        // Clear any previous connection error toasts
        clearConnectionErrorToast();
    });

    socket.on('disconnect', function(reason) {
        console.log('❌ Disconnected from Socket.IO - Reason:', reason);

        // Show connection error toast for unexpected disconnects
        if (reason === 'io server disconnect' || reason === 'io client disconnect') {
            console.log('🔄 Connection closed by server/client, will attempt reconnection');
        } else {
            showConnectionErrorToast();
        }
    });

    socket.on('connect_error', function(error) {
        console.error('🚫 Socket.IO connection error:', error);
        console.error('Error details:', {
            type: error.type,
            description: error.description,
            context: error.context
        });

        // Show connection error toast
        showConnectionErrorToast();
    });

    socket.on('reconnect', function(attemptNumber) {
        console.log('🔄 Socket.IO reconnected after', attemptNumber, 'attempts');
        clearConnectionErrorToast();
    });

    socket.on('reconnect_attempt', function(attemptNumber) {
        console.log('🔄 Socket.IO reconnection attempt', attemptNumber);
    });

    socket.on('reconnect_error', function(error) {
        console.error('🚫 Socket.IO reconnection error:', error);
    });

    socket.on('reconnect_failed', function() {
        console.error('❌ Socket.IO reconnection failed permanently');
        showConnectionErrorToast();
    });

    socket.on('new_update', function(data) {
        console.log('🔔 New update received via Socket.IO:', data);
        console.log('📦 Update data - ID:', data.id, 'Name:', data.name, 'Process:', data.process);
        showUpdateToast(data);
    });

    socket.on('connected', function(data) {
        console.log('🔗 Socket.IO connection confirmed:', data);
    });

    socket.on('error', function(error) {
        console.error('🚫 Socket.IO error:', error);
    });
}

// Export functions for global access
window.notifications = {
    toggle: toggleNotifications,
    markAllAsRead: markAllAsRead,
    add: addNotification,
    getUnreadCount: () => unreadCount
};

// Make functions globally available
window.toggleNotifications = toggleNotifications;
window.markAllAsRead = markAllAsRead;
window.toggleNotificationSound = toggleNotificationSound;
window.testNotificationSound = testNotificationSound;
window.forceSocketReconnect = forceSocketReconnect;

// Test function for notification sound (for debugging)
window.testNotificationSound = function() {
    console.log('🧪 Testing notification sound...');
    playNotificationSound();
};

// Connection error handling for Vercel stability
function showConnectionErrorToast() {
    const now = Date.now();

    // Check if we already have an active error toast to prevent piling
    if (connectionErrorToast && document.body.contains(connectionErrorToast)) {
        return;
    }

    // Only show error toast if it's been more than 30 seconds since last error
    if (now - lastConnectionErrorTime < 30000) {
        return;
    }

    lastConnectionErrorTime = now;
    connectionErrorCount++;

    // Only show error toast after 2 failed attempts (less aggressive than before)
    if (connectionErrorCount >= 2) {
        // Double-check and clear any existing toasts before creating new one
        clearConnectionErrorToast();

        connectionErrorToast = showToast(
            '⚠️ Real-time connection lost. Using offline mode.',
            'permanent'
        );
    }
}

function clearConnectionErrorToast() {
    if (connectionErrorToast) {
        closeToast(connectionErrorToast);
        connectionErrorToast = null;
    }
}

// Clear all connection error toasts from DOM to prevent piling
function clearAllConnectionErrorToasts() {
    // Find all toasts with the connection error message
    const errorToasts = document.querySelectorAll('.toast');

    errorToasts.forEach(toast => {
        const toastContent = toast.querySelector('.toast-content') || toast;
        if (toastContent && toastContent.innerHTML &&
            toastContent.innerHTML.includes('Real-time connection lost')) {
            closeToast(toast);
        }
    });

    // Also clear the tracked toast reference
    if (connectionErrorToast) {
        connectionErrorToast = null;
    }
}

// Test function for complete notification system (for debugging)
window.testNotificationSystem = function() {
    console.log('🧪 Testing complete notification system...');
    const testUpdate = {
        id: 'test-' + Date.now(),
        name: 'Test User',
        process: 'ABC',
        timestamp: new Date().toISOString()
    };
    showUpdateToast(testUpdate);
};

// Test Socket.IO connection status (for debugging)
window.testSocketConnection = function() {
    console.log('🧪 Testing Socket.IO connection...');

    if (!socket) {
        console.error('❌ Socket.IO not initialized');
        return;
    }

    console.log('Socket.IO status:', {
        connected: socket.connected,
        disconnected: socket.disconnected,
        id: socket.id,
        transport: socket.io?.engine?.transport?.name || 'unknown',
        readyState: socket.io?.engine?.readyState || 'unknown'
    });

    if (socket.connected) {
        console.log('✅ Socket.IO is connected');
        socket.emit('test_connection', {
            message: 'Test from browser',
            timestamp: new Date().toISOString()
        });
    } else {
        console.log('❌ Socket.IO is not connected');
    }
};

// Force reconnect Socket.IO (for debugging)
window.forceSocketReconnect = function() {
    console.log('🔄 Forcing Socket.IO reconnection...');

    if (socket) {
        socket.disconnect();
        setTimeout(() => {
            socket.connect();
        }, 1000);
    } else {
        console.log('❌ Socket.IO not initialized, reinitializing...');
        initializeSocketIO();
    }
};


