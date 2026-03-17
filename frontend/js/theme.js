/**
 * PatientPath AI — Theme Toggle
 * Default: Dark.  Optional light mode via .light-theme class.
 * Applies saved preference immediately to prevent flash.
 */
(function () {
    var saved = localStorage.getItem('pp_theme');
    // Only apply light-theme when explicitly saved as 'light'
    if (saved === 'light') {
        document.documentElement.classList.add('light-theme');
    }
    // Default (no saved preference, or 'dark') = dark — no class needed
})();

function toggleTheme() {
    var html    = document.documentElement;
    var isLight = html.classList.toggle('light-theme');
    localStorage.setItem('pp_theme', isLight ? 'light' : 'dark');

    var btn = document.getElementById('theme-toggle-btn');
    if (btn) {
        btn.innerHTML = isLight
            ? '<i class="fas fa-moon"></i>'
            : '<i class="fas fa-sun"></i>';
        btn.setAttribute('title',       isLight ? 'Switch to dark mode' : 'Switch to light mode');
        btn.setAttribute('aria-label',  isLight ? 'Switch to dark mode' : 'Switch to light mode');
    }
}
