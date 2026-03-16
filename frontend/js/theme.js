/**
 * PatientPath AI - Theme Toggle
 * Applies saved theme immediately (before paint) and provides toggle function.
 */

// Apply saved theme synchronously to prevent flash of wrong theme
(function () {
    var saved = localStorage.getItem('pp_theme');
    if (saved === 'light') {
        document.documentElement.classList.add('light-theme');
    }
})();

function toggleTheme() {
    var html = document.documentElement;
    var isLight = html.classList.toggle('light-theme');
    localStorage.setItem('pp_theme', isLight ? 'light' : 'dark');
    var btn = document.getElementById('theme-toggle-btn');
    if (btn) {
        btn.innerHTML = isLight
            ? '<i class="fas fa-moon"></i>'
            : '<i class="fas fa-sun"></i>';
        btn.title = isLight ? 'Switch to dark mode' : 'Switch to light mode';
    }
}
