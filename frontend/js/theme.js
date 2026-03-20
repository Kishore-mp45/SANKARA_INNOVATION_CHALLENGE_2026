/**
 * PatientPath AI - Global Theme Manager
 */

(function () {
    const LOCAL_STORAGE_KEY = 'pp_theme';

    // 1. Get initial theme (default to light as requested)
    let currentTheme = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!currentTheme) {
        currentTheme = 'light';
        localStorage.setItem(LOCAL_STORAGE_KEY, currentTheme);
    }

    // Function to apply theme classes to document
    function applyTheme() {
        if (currentTheme === 'light') {
            document.documentElement.classList.add('light-theme');
            document.documentElement.classList.remove('theme-dark');
            if (document.body) document.body.classList.remove('theme-dark');
        } else {
            document.documentElement.classList.remove('light-theme');
            document.documentElement.classList.add('theme-dark');
            if (document.body) document.body.classList.add('theme-dark');
        }
    }

    // Apply immediately to prevent flash
    applyTheme();

    document.addEventListener('DOMContentLoaded', () => {
        applyTheme(); // Ensure body also gets the class

        // Give pages time to render their own headers/navbars, we inject floating button
        const btn = document.createElement('button');
        btn.id = 'global-theme-toggle';
        btn.title = 'Toggle Theme';
        
        // CSS for the floating button (Top right corner on all pages)
        Object.assign(btn.style, {
            position: 'fixed',
            top: '20px',
            right: '25px',
            zIndex: '999999',
            width: '45px',
            height: '45px',
            borderRadius: '50%',
            backgroundColor: currentTheme === 'light' ? '#f8fafc' : '#1e293b',
            color: currentTheme === 'light' ? '#334155' : '#f8fafc',
            border: '1px solid ' + (currentTheme === 'light' ? '#cbd5e1' : '#334155'),
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.2rem',
            transition: 'all 0.3s ease'
        });

        const updateIcon = () => {
            btn.innerHTML = currentTheme === 'light' ? '<i class="fas fa-moon"></i>' : '<i class="fas fa-sun"></i>';
            btn.style.backgroundColor = currentTheme === 'light' ? '#f8fafc' : '#1e293b';
            btn.style.color = currentTheme === 'light' ? '#334155' : '#f8fafc';
            btn.style.borderColor = currentTheme === 'light' ? '#cbd5e1' : '#334155';
        };
        updateIcon();

        // Hover effects
        btn.addEventListener('mouseenter', () => {
            btn.style.transform = 'scale(1.1)';
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'scale(1)';
        });

        // Click handler toggles state globally
        btn.addEventListener('click', () => {
            currentTheme = currentTheme === 'light' ? 'dark' : 'light';
            localStorage.setItem(LOCAL_STORAGE_KEY, currentTheme);
            applyTheme();
            updateIcon();

            // Fire a custom event for local pages to react if they want
            window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: currentTheme } }));
        });

        const staticContainer = document.getElementById('theme-toggle-container');
        if (staticContainer) {
            Object.assign(btn.style, {
                position: 'relative',
                top: 'auto',
                right: 'auto',
                zIndex: 'auto',
                width: '38px',
                height: '38px',
                fontSize: '1rem',
                boxShadow: 'none'
            });
            staticContainer.appendChild(btn);
        } else {
            document.body.appendChild(btn);
        }

        // Optional: Remove local toggles if any page had them to avoid duplicates
        const localToggle = document.getElementById('theme-toggle');
        if (localToggle) {
            localToggle.style.display = 'none';
        }
    });

})();

window.toggleTheme = function() {
    const btn = document.getElementById('global-theme-toggle');
    if(btn) btn.click();
};
