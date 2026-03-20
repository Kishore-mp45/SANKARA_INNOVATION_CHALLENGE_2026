/**
 * PatientPath AI - Shared Toast Notification Utility
 * Provides consistent toast notifications across all pages.
 * Include this file after theme.js and before page-specific scripts.
 */

(function () {
    'use strict';

    // Create toast container if not present
    function getOrCreateContainer() {
        var container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText = 'position:fixed;bottom:2rem;right:2rem;z-index:10001;';
            document.body.appendChild(container);
        }
        return container;
    }

    /**
     * Show a toast notification.
     * @param {string} message - Text to display
     * @param {string} type - 'success' | 'error' | 'info'
     * @param {number} duration - Auto-dismiss in ms (default 3000)
     */
    window.showToast = function (message, type, duration) {
        var container = getOrCreateContainer();
        var toast = document.createElement('div');
        duration = duration || 3000;

        var borderColor = '#0ea5e9'; // info/default (primary blue)
        var icon = 'fa-info-circle';
        if (type === 'success') { borderColor = '#10b981'; icon = 'fa-check-circle'; }
        if (type === 'error') { borderColor = '#ef4444'; icon = 'fa-exclamation-circle'; }

        toast.style.cssText =
            'background:var(--sidebar-bg, #fff);' +
            'border:1px solid var(--border-color, #e2e8f0);' +
            'border-left:4px solid ' + borderColor + ';' +
            'color:var(--text-main, #1a2332);' +
            'padding:0.85rem 1.25rem;' +
            'border-radius:8px;' +
            'margin-bottom:0.5rem;' +
            'box-shadow:0 4px 16px rgba(0,0,0,0.15);' +
            'display:flex;align-items:center;gap:0.75rem;' +
            'min-width:280px;max-width:400px;' +
            'animation:toastSlideIn 0.3s ease-out;' +
            'font-size:0.9rem;line-height:1.4;';

        toast.innerHTML = '<i class="fas ' + icon + '" style="color:' + borderColor + ';flex-shrink:0;font-size:1rem;"></i>' +
            '<span style="flex:1;">' + message + '</span>' +
            '<button onclick="this.parentElement.remove()" style="background:none;border:none;color:var(--text-muted,#94a3b8);cursor:pointer;padding:0;font-size:0.85rem;flex-shrink:0;"><i class="fas fa-times"></i></button>';

        container.appendChild(toast);

        setTimeout(function () {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s ease-in';
            setTimeout(function () { toast.remove(); }, 300);
        }, duration);
    };

    // Inject animation keyframes if not present
    if (!document.getElementById('toast-keyframes')) {
        var style = document.createElement('style');
        style.id = 'toast-keyframes';
        style.textContent =
            '@keyframes toastSlideIn { from { transform:translateX(100%); opacity:0; } to { transform:translateX(0); opacity:1; } }';
        document.head.appendChild(style);
    }
})();
