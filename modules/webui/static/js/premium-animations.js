/**
 * ADLA Premium Animations
 * Adds smooth transitions, subtle animations, and interaction enhancements
 * for a high-end, premium user experience
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize animations
    initPremiumAnimations();
});

function initPremiumAnimations() {
    // Add fade-in animation to key elements
    addEntryAnimations();
    
    // Add hover effects for interactive elements
    enhanceHoverEffects();
    
    // Add scroll animations
    addScrollAnimations();
    
    // Add subtle background animations
    addBackgroundAnimations();
    
    // Initialize counters for statistics
    initCounters();
    
    console.log('Premium animations initialized');
}

/**
 * Add entry animations to key page elements
 */
function addEntryAnimations() {
    // Dashboard header fade in
    const dashboardHeader = document.querySelector('.dashboard-header');
    if (dashboardHeader) {
        dashboardHeader.classList.add('fade-in');
    }
    
    // Cards slide up with staggered delay
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('slide-up');
        }, 100 + (index * 100)); // Stagger the animations
    });
    
    // Property detail elements
    const propertyDetailSections = document.querySelectorAll('#property-detail .row');
    propertyDetailSections.forEach((section, index) => {
        setTimeout(() => {
            section.classList.add('fade-in');
        }, 200 + (index * 150));
    });
}

/**
 * Enhance hover effects for interactive elements
 */
function enhanceHoverEffects() {
    // Add subtle scale effect to buttons
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = 'var(--adla-shadow-md)';
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.boxShadow = '';
        });
    });
    
    // Add hover effect to table rows
    document.querySelectorAll('tbody tr').forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = 'rgba(241, 193, 98, 0.05)';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
    });
    
    // Add hover effect to cards
    document.querySelectorAll('.card:not(.shadow-hover)').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = 'var(--adla-shadow-lg)';
            this.style.transition = 'var(--adla-transition-normal)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.boxShadow = '';
        });
    });
}

/**
 * Add animations triggered by scrolling
 */
function addScrollAnimations() {
    // Animate elements when they enter the viewport
    const scrollAnimElements = document.querySelectorAll('.visualization-card, .card:not(.slide-up)');
    
    // Create an intersection observer
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('slide-up');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.2
    });
    
    // Observe each element
    scrollAnimElements.forEach(el => {
        observer.observe(el);
    });
}

/**
 * Add subtle background animations
 */
function addBackgroundAnimations() {
    // Add subtle gradient animation to dashboard header
    const header = document.querySelector('.dashboard-header');
    if (header) {
        const overlay = document.createElement('div');
        overlay.classList.add('gradient-overlay');
        overlay.style.position = 'absolute';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.background = 'linear-gradient(135deg, transparent 0%, rgba(241, 193, 98, 0.05) 100%)';
        overlay.style.opacity = '0';
        overlay.style.transition = 'opacity 3s ease-in-out';
        overlay.style.zIndex = '1';
        
        header.appendChild(overlay);
        
        // Animate the overlay
        setTimeout(() => {
            overlay.style.opacity = '1';
        }, 500);
    }
}

/**
 * Initialize animated counters for statistics
 */
function initCounters() {
    const counters = document.querySelectorAll('.counter-value');
    
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-count'), 10);
        const duration = 2000; // 2 seconds
        const step = Math.max(1, Math.floor(target / (duration / 30))); // Update every 30ms
        
        let current = 0;
        const counterInterval = setInterval(() => {
            current += step;
            if (current >= target) {
                current = target;
                clearInterval(counterInterval);
            }
            counter.textContent = current.toLocaleString();
        }, 30);
    });
}

/**
 * Update chart animations
 * Call this function when initializing charts to make them more premium
 */
function enhanceChartAnimations(chart) {
    if (!chart) return;
    
    // For Chart.js charts
    if (chart.options) {
        // Add smoother animations
        chart.options.animation = {
            duration: 1500,
            easing: 'easeOutQuart',
            delay: (context) => context.dataIndex * 100
        };
        
        // Update the chart
        chart.update();
    }
}

/**
 * Create a pulsing animation effect for key indicators
 * @param {string} selector - Element selector to apply the effect to
 */
function addPulseEffect(selector) {
    const elements = document.querySelectorAll(selector);
    
    elements.forEach(el => {
        el.classList.add('pulse-animation');
        
        // Add CSS if not already in style
        if (!document.getElementById('pulse-animation-style')) {
            const style = document.createElement('style');
            style.id = 'pulse-animation-style';
            style.textContent = `
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                    100% { transform: scale(1); }
                }
                .pulse-animation {
                    animation: pulse 2s infinite ease-in-out;
                }
            `;
            document.head.appendChild(style);
        }
    });
}

/**
 * Add a typing effect to a text element
 * @param {string} selector - Element selector to apply the effect to
 * @param {string} text - Text to type
 * @param {number} speed - Typing speed in ms
 */
function addTypingEffect(selector, text, speed = 50) {
    const element = document.querySelector(selector);
    if (!element) return;
    
    element.textContent = '';
    let i = 0;
    
    function typeWriter() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            setTimeout(typeWriter, speed);
        }
    }
    
    typeWriter();
}

// Export functions for use in other scripts
window.premiumAnimations = {
    enhanceChartAnimations,
    addPulseEffect,
    addTypingEffect
}; 