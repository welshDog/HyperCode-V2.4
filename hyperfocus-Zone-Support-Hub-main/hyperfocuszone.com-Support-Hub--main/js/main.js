// Hyperfocus Support Page - JavaScript Functionality
'use strict';

class HyperfocusSupport {
    constructor() {
        this.init();
    }

    init() {
        this.setupAccessibilityControls();
        this.setupAnimations();
        this.setupProgressBars();
        this.setupMetricsUpdater();
        this.setupFormEnhancements();
        this.setupAnalytics();
        console.log('🚀 Hyperfocus Support initialized');
    }

    // Accessibility Controls
    setupAccessibilityControls() {
        // Motion toggle
        const motionToggle = document.getElementById('motionToggle');
        if (motionToggle) {
            motionToggle.addEventListener('click', () => {
                document.body.classList.toggle('reduced-motion');
                const isReduced = document.body.classList.contains('reduced-motion');
                motionToggle.setAttribute('aria-pressed', isReduced);
                localStorage.setItem('reduced-motion', isReduced);
                this.showNotification(isReduced ? 'Animations reduced' : 'Animations enabled');
            });

            // Load saved preference
            const savedMotionPref = localStorage.getItem('reduced-motion') === 'true';
            if (savedMotionPref) {
                document.body.classList.add('reduced-motion');
                motionToggle.setAttribute('aria-pressed', 'true');
            }
        }

        // Font toggle for dyslexia-friendly font
        const fontToggle = document.getElementById('fontToggle');
        if (fontToggle) {
            fontToggle.addEventListener('click', () => {
                document.body.classList.toggle('dyslexic-font');
                const isDyslexicFont = document.body.classList.contains('dyslexic-font');
                fontToggle.setAttribute('aria-pressed', isDyslexicFont);
                localStorage.setItem('dyslexic-font', isDyslexicFont);
                this.showNotification(isDyslexicFont ? 'Dyslexic-friendly font enabled' : 'Default font restored');
            });

            // Load saved preference
            const savedFontPref = localStorage.getItem('dyslexic-font') === 'true';
            if (savedFontPref) {
                document.body.classList.add('dyslexic-font');
                fontToggle.setAttribute('aria-pressed', 'true');
            }
        }

        // Focus mode toggle
        const focusToggle = document.getElementById('focusToggle');
        if (focusToggle) {
            focusToggle.addEventListener('click', () => {
                document.body.classList.toggle('focus-mode');
                const isFocusMode = document.body.classList.contains('focus-mode');
                focusToggle.setAttribute('aria-pressed', isFocusMode);
                localStorage.setItem('focus-mode', isFocusMode);
                this.showNotification(isFocusMode ? 'Focus mode enabled' : 'Focus mode disabled');
            });

            // Load saved preference
            const savedFocusPref = localStorage.getItem('focus-mode') === 'true';
            if (savedFocusPref) {
                document.body.classList.add('focus-mode');
                focusToggle.setAttribute('aria-pressed', 'true');
            }
        }

        // Respect system preferences
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            document.body.classList.add('reduced-motion');
            if (motionToggle) motionToggle.setAttribute('aria-pressed', 'true');
        }
    }

    // Smooth scroll animations
    setupAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);

        // Observe all sections for fade-in animation
        document.querySelectorAll('.section').forEach(section => {
            section.style.opacity = '0';
            section.style.transform = 'translateY(50px)';
            section.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(section);
        });

        // Add hover effects to cards
        document.querySelectorAll('.tier-card, .support-card, .contact-item').forEach(card => {
            card.addEventListener('mouseenter', () => {
                if (!document.body.classList.contains('reduced-motion')) {
                    card.style.transform = 'translateY(-10px)';
                }
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
            });
        });
    }

    // Progress bar animations
    setupProgressBars() {
        const progressBars = document.querySelectorAll('.progress-bar');
        progressBars.forEach(bar => {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        // Trigger progress animation when visible
                        setTimeout(() => {
                            bar.style.transition = 'width 2s ease';
                        }, 500);
                        observer.unobserve(entry.target);
                    }
                });
            });
            observer.observe(bar);
        });
    }

    // Update metrics with realistic growth simulation
    setupMetricsUpdater() {
        const updateMetrics = () => {
            const currentDate = new Date();
            const baseValues = {
                supporters: 2047,
                discordMembers: 2000,
                monthlyRevenue: 6800,
                countries: 184
            };

            // Add some realistic growth simulation
            const dayOfYear = Math.floor((currentDate - new Date(currentDate.getFullYear(), 0, 0)) / 86400000);
            const growthFactor = Math.floor(dayOfYear / 30) + Math.floor(Math.random() * 20);

            const metrics = {
                supporters: baseValues.supporters + growthFactor + Math.floor(Math.random() * 10),
                discordMembers: baseValues.discordMembers + growthFactor,
                monthlyRevenue: baseValues.monthlyRevenue + Math.floor(growthFactor * 2.5),
                countries: Math.min(195, baseValues.countries + Math.floor(growthFactor / 50))
            };

            // Update displays
            const supportersEl = document.getElementById('live-supporters');
            const discordCountEl = document.getElementById('discord-count');
            const fundingTextEl = document.getElementById('funding-text');

            if (supportersEl) {
                this.animateNumber(supportersEl, parseInt(supportersEl.textContent.replace(/,/g, '')), metrics.supporters);
            }

            if (discordCountEl) {
                discordCountEl.textContent = metrics.discordMembers.toLocaleString() + '+';
            }

            // Update funding progress
            const fundingProgress = document.getElementById('funding-progress');
            if (fundingProgress && fundingTextEl) {
                const percentage = Math.floor((metrics.monthlyRevenue / 10000) * 100);
                fundingProgress.style.width = percentage + '%';
                fundingProgress.setAttribute('aria-valuenow', percentage);
                fundingTextEl.textContent = 
                    `$${metrics.monthlyRevenue.toLocaleString()} of $10,000 monthly goal reached (${percentage}%)`;
            }
        };

        // Initial update after a delay
        setTimeout(updateMetrics, 2000);

        // Update every 45 seconds for demo effect
        setInterval(updateMetrics, 45000);
    }

    // Animate number changes
    animateNumber(element, start, end) {
        const duration = 2000;
        const startTime = performance.now();

        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            const current = Math.floor(start + (end - start) * this.easeOutCubic(progress));
            element.textContent = current.toLocaleString();

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    }

    // Easing function for smooth animations
    easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    // Form enhancements
    setupFormEnhancements() {
        // Add focus management for donation buttons
        document.querySelectorAll('.donation-btn').forEach(btn => {
            btn.addEventListener('focus', function() {
                this.style.outline = '3px solid var(--focus-color)';
                this.style.outlineOffset = '2px';
            });

            btn.addEventListener('blur', function() {
                this.style.outline = '';
                this.style.outlineOffset = '';
            });

            // Add keyboard navigation
            btn.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
// Hyperfocus Support Page - JavaScript Functionality
'use strict';

class HyperfocusSupport {
    constructor() {
        this.init();
    }

    init() {
        this.setupAccessibilityControls();
        this.setupAnimations();
        this.setupProgressBars();
        this.setupMetricsUpdater();
        this.setupFormEnhancements();
        this.setupAnalytics();
        console.log('ðŸš€ Hyperfocus Support initialized');
    }

    // Accessibility Controls
    setupAccessibilityControls() {
        // Motion toggle
        const motionToggle = document.getElementById('motionToggle');
        if (motionToggle) {
            motionToggle.addEventListener('click', () => {
                document.body.classList.toggle('reduced-motion');
                const isReduced = document.body.classList.contains('reduced-motion');
                motionToggle.setAttribute('aria-pressed', isReduced);
                localStorage.setItem('reduced-motion', isReduced);
                this.showNotification(isReduced ? 'Animations reduced' : 'Animations enabled');
            });

            // Load saved preference
            const savedMotionPref = localStorage.getItem('reduced-motion') === 'true';
            if (savedMotionPref) {
                document.body.classList.add('reduced-motion');
                motionToggle.setAttribute('aria-pressed', 'true');
            }
        }

        // Font toggle for dyslexia-friendly font
        const fontToggle = document.getElementById('fontToggle');
        if (fontToggle) {
            fontToggle.addEventListener('click', () => {
                document.body.classList.toggle('dyslexic-font');
                const isDyslexicFont = document.body.classList.contains('dyslexic-font');
                fontToggle.setAttribute('aria-pressed', isDyslexicFont);
                localStorage.setItem('dyslexic-font', isDyslexicFont);
                this.showNotification(isDyslexicFont ? 'Dyslexic-friendly font enabled' : 'Default font restored');
            });

            // Load saved preference
            const savedFontPref = localStorage.getItem('dyslexic-font') === 'true';
            if (savedFontPref) {
                document.body.classList.add('dyslexic-font');
                fontToggle.setAttribute('aria-pressed', 'true');
            }
        }

        // Focus mode toggle
        const focusToggle = document.getElementById('focusToggle');
        if (focusToggle) {
            focusToggle.addEventListener('click', () => {
                document.body.classList.toggle('focus-mode');
                const isFocusMode = document.body.classList.contains('focus-mode');
                focusToggle.setAttribute('aria-pressed', isFocusMode);
                localStorage.setItem('focus-mode', isFocusMode);
                this.showNotification(isFocusMode ? 'Focus mode enabled' : 'Focus mode disabled');
            });

            // Load saved preference
            const savedFocusPref = localStorage.getItem('focus-mode') === 'true';
            if (savedFocusPref) {
                document.body.classList.add('focus-mode');
                focusToggle.setAttribute('aria-pressed', 'true');
            }
        }

        // Respect system preferences
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            document.body.classList.add('reduced-motion');
            if (motionToggle) motionToggle.setAttribute('aria-pressed', 'true');
        }
    }

    // Smooth scroll animations
    setupAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);

        // Observe all sections for fade-in animation
        document.querySelectorAll('.section').forEach(section => {
            section.style.opacity = '0';
            section.style.transform = 'translateY(50px)';
            section.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(section);
        });

        // Add hover effects to cards
        document.querySelectorAll('.tier-card, .support-card, .contact-item').forEach(card => {
            card.addEventListener('mouseenter', () => {
                if (!document.body.classList.contains('reduced-motion')) {
                    card.style.transform = 'translateY(-10px)';
                }
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
            });
        });
    }

    // Progress bar animations
    setupProgressBars() {
        const progressBars = document.querySelectorAll('.progress-bar');
        progressBars.forEach(bar => {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        // Trigger progress animation when visible
                        setTimeout(() => {
                            bar.style.transition = 'width 2s ease';
                        }, 500);
                        observer.unobserve(entry.target);
                    }
                });
            });
            observer.observe(bar);
        });
    }

    // Update metrics with realistic growth simulation - RESET TO 0
    setupMetricsUpdater() {
        const updateMetrics = () => {
            const currentDate = new Date();
            const baseValues = {
                supporters: 0,           // RESET TO 0
                discordMembers: 0,       // RESET TO 0  
                monthlyRevenue: 0,       // RESET TO 0
                countries: 0             // RESET TO 0
            };

            // Start from 0 - no growth simulation needed initially
            const metrics = {
                supporters: 0,
                discordMembers: 0,
                monthlyRevenue: 0,
                countries: 0
            };

            // Update displays
            const supportersEl = document.getElementById('live-supporters');
            const discordCountEl = document.getElementById('discord-count');
            const fundingTextEl = document.getElementById('funding-text');

            if (supportersEl) {
                supportersEl.textContent = '0';
            }

            if (discordCountEl) {
                discordCountEl.textContent = '0+';
            }

            // Update funding progress
            const fundingProgress = document.getElementById('funding-progress');
            if (fundingProgress && fundingTextEl) {
                const percentage = 0; // Starting at 0%
                fundingProgress.style.width = '0%';
                fundingProgress.setAttribute('aria-valuenow', '0');
                fundingTextEl.textContent = `Â£0 of Â£10,000 monthly goal reached (0%)`;
            }
        };

        // Initial update after a delay
        setTimeout(updateMetrics, 500);
    }

    // Animate number changes
    animateNumber(element, start, end) {
        const duration = 2000;
        const startTime = performance.now();

        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const current = Math.floor(start + (end - start) * this.easeOutCubic(progress));
            
            element.textContent = current.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }

    // Easing function for smooth animations
    easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    // Form enhancements
    setupFormEnhancements() {
        // Add focus management for donation buttons
        document.querySelectorAll('.donation-btn').forEach(btn => {
            btn.addEventListener('focus', function() {
                this.style.outline = '3px solid var(--focus-color)';
                this.style.outlineOffset = '2px';
            });

            btn.addEventListener('blur', function() {
                this.style.outline = '';
                this.style.outlineOffset = '';
            });

            // Add keyboard navigation
            btn.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.click();
                }
            });
        });

        // Smooth scroll for skip links
        document.querySelectorAll('.skip-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(link.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ 
                        behavior: 'smooth',
                        block: 'start'
                    });
                    target.focus();
                }
            });
        });
    }

    // Analytics and tracking
    setupAnalytics() {
        // Track donation button clicks
        document.querySelectorAll('.donation-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = btn.textContent.trim();
                const href = btn.href || btn.getAttribute('data-action');
                
                console.log('Donation action clicked:', action, href);
                
                // Track accessibility preference usage
                this.trackEvent('donation_click', {
                    action: action,
                    reduced_motion: document.body.classList.contains('reduced-motion'),
                    dyslexic_font: document.body.classList.contains('dyslexic-font'),
                    focus_mode: document.body.classList.contains('focus-mode')
                });

                // Add visual feedback
                this.showClickFeedback(btn);
            });
        });

        // Track accessibility control usage
        document.querySelectorAll('.accessibility-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.trackEvent('accessibility_control_used', {
                    control: btn.id,
                    timestamp: new Date().toISOString()
                });
            });
        });

        // Track scroll depth
        this.setupScrollTracking();
    }

    // Track scroll depth for engagement analytics
    setupScrollTracking() {
        let maxScroll = 0;
        const trackingPoints = [25, 50, 75, 90, 100];
        const tracked = new Set();

        const trackScroll = () => {
            const scrollPercent = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
            maxScroll = Math.max(maxScroll, scrollPercent);

            trackingPoints.forEach(point => {
                if (scrollPercent >= point && !tracked.has(point)) {
                    tracked.add(point);
                    this.trackEvent('scroll_depth', { percent: point });
                }
            });
        };

        window.addEventListener('scroll', this.throttle(trackScroll, 250));
    }

    // Utility functions
    trackEvent(eventName, properties = {}) {
        // In a real implementation, this would send to analytics service
        console.log(`ðŸ“Š Event: ${eventName}`, properties);
        
        // Example: Send to Google Analytics
        // if (typeof gtag !== 'undefined') {
        //     gtag('event', eventName, properties);
        // }
    }

    showNotification(message) {
        // Create temporary notification
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: var(--neon-purple);
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 1000;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    showClickFeedback(element) {
        if (document.body.classList.contains('reduced-motion')) return;
        
        element.style.transform = 'scale(0.95)';
        setTimeout(() => {
            element.style.transform = '';
        }, 150);
    }

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// Add notification animations to CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new HyperfocusSupport();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        console.log('ðŸ‘€ Page visible - user returned');
    }
});

// Error handling
window.addEventListener('error', (e) => {
    console.error('ðŸ’¥ JavaScript error:', e.error);
});

// Keyboard shortcuts for power users
document.addEventListener('keydown', (e) => {
    // Alt + M = Toggle motion
    if (e.altKey && e.key === 'm') {
        e.preventDefault();
        document.getElementById('motionToggle')?.click();
    }
    // Alt + F = Toggle font
    if (e.altKey && e.key === 'f') {
        e.preventDefault();
        document.getElementById('fontToggle')?.click();
    }
    // Alt + Z = Toggle focus mode
    if (e.altKey && e.key === 'z') {
        e.preventDefault();
        document.getElementById('focusToggle')?.click();
    }
});
