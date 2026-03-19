/**
 * PatientPath AI - Theme (Light Mode Forced)
 * Forces light theme globally. Toggle disabled.
 */

// Force light theme immediately
(function () {
    document.documentElement.classList.add('light-theme');
    localStorage.setItem('pp_theme', 'light');
})();

// No-op: keeps existing calls from erroring
function toggleTheme() { }
