// Updates Banner System - Shows recent updates from past 24hrs when bell icon is clicked
"use strict";

class UpdatesBanner {
    constructor() {
        this.banner = null;
        this.bannerList = null;
        this.isVisible = false;
        this.clickTimeout = null;
        this.touchStartY = null;
        this.updateCheckTimeout = null;
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        this.banner = document.getElementById('updates-banner');
        this.bannerList = document.getElementById('updates-banner-list');
        
        // Implement event delegation for all click handlers
        document.addEventListener('click', (event) => {
            // Handle outside clicks
            const bellContainer = document.querySelector('.notification-container');
            if (this.isVisible && bellContainer && !bellContainer.contains(event.target)) {
                this.closeBanner();
                return;
            }

            // Handle update item clicks
            if (event.target.closest('.banner-update-item')) {
                const item = event.target.closest('.banner-update-item');
                const updateId = item.getAttribute('data-update-id');
                if (updateId) {
                    this.handleUpdateClick(updateId);
                }
                return;
            }

            // Handle "View All" clicks
            if (event.target.closest('.banner-view-all')) {
                this.handleViewAllClick();
                return;
            }
        }, { passive: true }); // Add passive flag for better scroll performance

        // Implement touch events for mobile
        if ('ontouchstart' in window) {
            document.addEventListener('touchstart', this.handleTouch.bind(this), { passive: true });
        }

        // Check for recent updates and show badge
        this.checkForRecentUpdatesAndShowBadge();
        
        // Set up periodic checking with random jitter to prevent thundering herd
        const interval = 5 * 60 * 1000; // 5 minutes
        const jitter = Math.random() * 30000; // Random delay up to 30 seconds
        setInterval(() => this.checkForRecentUpdatesAndShowBadge(), interval + jitter);
    }

    async toggleBanner() {
        if (this.isVisible) {
            this.closeBanner();
        } else {
            await this.showBanner();
        }
    }

    async showBanner() {
        if (!this.banner || !this.bannerList) return;

        // Show loading state immediately
        this.bannerList.innerHTML = `
            <div class="banner-loading">
                <p style="text-align: center; color: var(--gray-500); padding: var(--space-4);">
                    Loading updates...
                </p>
            </div>
        `;
        this.banner.style.display = 'block';
        this.isVisible = true;

        try {
            // Add cache busting and timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);

            const response = await fetch('/api/recent-updates?' + new URLSearchParams({
                _: Date.now() // Cache busting
            }), {
                signal: controller.signal,
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            clearTimeout(timeoutId);
            const data = await response.json();

            if (data.success && data.updates) {
                this.populateBanner(data.updates);
            } else {
                this.showEmptyBanner();
            }
        } catch (error) {
            console.error('Error fetching recent updates:', error);
            this.showEmptyBanner();
        }
    }

    populateBanner(updates) {
        if (!this.bannerList) return;

        if (updates.length === 0) {
            this.bannerList.innerHTML = `
                <div class="banner-empty-state">
                    <p style="text-align: center; color: var(--gray-500); padding: var(--space-4);">
                        No updates in the past 24 hours
                    </p>
                </div>
            `;
            return;
        }

        // Limit to 3 most recent updates to prevent clutter
        const limitedUpdates = updates.slice(0, 3);

        this.bannerList.innerHTML = limitedUpdates.map(update => `
            <div class="banner-update-item" onclick="goToUpdate('${update.id}')">
                <div class="banner-update-title">${this.truncateText(update.message, 60)}</div>
                <div class="banner-update-meta">
                    <span>${update.name}</span>
                    <span class="banner-update-process">${update.process}</span>
                </div>
            </div>
        `).join('');

        // Add "View All Updates" link if there are more than 3 updates
        if (updates.length > 3) {
            this.bannerList.innerHTML += `
                <div class="banner-view-all" onclick="goToAllUpdates()" style="
                    text-align: center;
                    padding: var(--space-3);
                    border-top: 1px solid var(--gray-200);
                    color: var(--primary-600);
                    cursor: pointer;
                    font-weight: 500;
                    font-size: 0.9rem;
                ">
                    View All Updates (${updates.length} total)
                </div>
            `;
        }
    }

    showEmptyBanner() {
        if (!this.banner || !this.bannerList) return;

        this.bannerList.innerHTML = `
            <div class="banner-empty-state">
                <p style="text-align: center; color: var(--gray-500); padding: var(--space-4);">
                    No recent updates available
                </p>
            </div>
        `;
        this.banner.style.display = 'block';
        this.isVisible = true;
    }

    closeBanner() {
        if (this.banner) {
            this.banner.style.display = 'none';
            this.isVisible = false;
        }
    }

    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    handleUpdateClick(updateId) {
        // Debounce click handling
        if (this.clickTimeout) {
            clearTimeout(this.clickTimeout);
        }
        
        this.clickTimeout = setTimeout(() => {
            this.closeBanner();
            window.location.href = `/updates?highlight_update=${updateId}`;
        }, 50);
    }

    handleViewAllClick() {
        // Debounce click handling
        if (this.clickTimeout) {
            clearTimeout(this.clickTimeout);
        }
        
        this.clickTimeout = setTimeout(() => {
            this.closeBanner();
            window.location.href = '/updates';
        }, 50);
    }

    handleTouch(event) {
        // Store touch start position
        this.touchStartY = event.touches[0].clientY;
        
        // Add touch move and end handlers
        document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: true });
        document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });
    }

    handleTouchMove(event) {
        if (!this.touchStartY) return;
        
        const touchY = event.touches[0].clientY;
        const diff = touchY - this.touchStartY;
        
        // If scrolling down more than 50px, close the banner
        if (diff > 50) {
            this.closeBanner();
        }
    }

    handleTouchEnd() {
        // Clean up touch tracking
        this.touchStartY = null;
        document.removeEventListener('touchmove', this.handleTouchMove.bind(this));
        document.removeEventListener('touchend', this.handleTouchEnd.bind(this));
    }

    async checkForRecentUpdatesAndShowBadge() {
        try {
            const response = await fetch('/api/latest-update-time');
            const data = await response.json();
            
            if (data.success && data.latest_timestamp) {
                const latestTime = new Date(data.latest_timestamp);
                const now = new Date();
                const diffHours = (now - latestTime) / (1000 * 60 * 60);
                
                const badge = document.getElementById('bell-badge');
                
                if (badge) {
                    if (diffHours <= 24) {
                        badge.style.display = 'block';
                    } else {
                        badge.style.display = 'none';
                    }
                }
            } else {
                const badge = document.getElementById('bell-badge');
                if (badge) {
                    badge.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error checking for recent updates:', error);
            const badge = document.getElementById('bell-badge');
            if (badge) {
                badge.style.display = 'none';
            }
        }
    }
}

// Initialize the updates banner and expose global methods
(() => {
    // Create instance
    window.updatesBanner = new UpdatesBanner();

    // Expose methods for onclick handlers
    window.toggleUpdatesBanner = () => window.updatesBanner?.toggleBanner();
    window.closeUpdatesBanner = () => window.updatesBanner?.closeBanner();
    window.goToUpdate = (updateId) => {
        window.updatesBanner?.closeBanner();
        window.location.href = `/updates?highlight_update=${updateId}`;
    };
    window.goToAllUpdates = () => {
        window.updatesBanner?.closeBanner();
        window.location.href = '/updates';
    };
})();
