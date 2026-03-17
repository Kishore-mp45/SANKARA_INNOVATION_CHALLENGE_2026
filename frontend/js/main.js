// Main.js - Shared Logic

// Removed by user request

window.logout = function () {
    const token = sessionStorage.getItem('authToken');
    if (token) {
        // Fire-and-forget server-side token invalidation
        fetch('/auth/logout', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token }
        }).catch(() => {});
    }
    sessionStorage.removeItem('authToken');
    sessionStorage.removeItem('currentUser');
    sessionStorage.removeItem('currentRole');
    sessionStorage.removeItem('currentDept');
    sessionStorage.removeItem('currentName');
    sessionStorage.removeItem('currentPatientId');
    window.location.href = 'login.html';
}

// Global helper: add Authorization header to fetch requests
window.authFetch = function (url, options = {}) {
    const token = sessionStorage.getItem('authToken');
    if (token) {
        options.headers = Object.assign({ 'Authorization': 'Bearer ' + token }, options.headers || {});
    }
    return fetch(url, options);
}


// RBAC: Role Definitions
const USER_ROLES = {
    admin: {
        allowed_pages: ['index.html', 'occupancy.html', 'heatmap.html', 'metrics.html', 'alerts.html', 'charts.html', 'prediction.html', 'video.html', 'admin_dashboard.html', 'notification_center.html', 'escalation_reports.html', 'resource_allocation.html'],
        label: 'Administrator'
    },
    doctor: {
        allowed_pages: ['index.html', 'occupancy.html', 'alerts.html', 'video.html', 'doctor_dashboard.html', 'doctor_workload.html', 'doctor_activity.html', 'doctor_dept_insights.html', 'doctor_escalate.html'],
        label: 'Doctor'
    },
    staff: {
        allowed_pages: ['index.html', 'occupancy.html', 'staff_panel.html', 'staff_activity.html', 'staff_allocation.html', 'bottleneck_warnings.html', 'patient_search.html', 'escalate_issue.html', 'department_performance.html', 'department_insights.html'],
        label: 'Hospital Staff'
    },
    patient: {
        allowed_pages: ['index.html', 'patient_dashboard.html', 'patient_activity.html', 'hospital_load_status.html', 'waiting_time_trend.html', 'navigation.html'],
        label: 'Patient'
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // 1. RBAC Check
    const currentRole = sessionStorage.getItem('currentRole');
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';

    // Skip check for login page
    if (currentPage === 'login.html') return;

    if (!currentRole) {
        window.location.href = 'login.html';
        return;
    }

    const roleConfig = USER_ROLES[currentRole];

    // Redirect if role is invalid or page is not allowed
    if (!roleConfig || !roleConfig.allowed_pages.includes(currentPage)) {
        // Build a safe redirect
        if (roleConfig && roleConfig.allowed_pages.length > 0) {
            // Redirect to their first allowed page (usually index.html)
            // But prevent infinite loops if index is allowed
            if (currentPage !== 'index.html') {
                window.location.href = 'index.html';
            } else {
                // If they are blocked from index, send to login
                if (!roleConfig.allowed_pages.includes('index.html')) {
                    window.location.href = 'login.html';
                }
            }
        } else {
            sessionStorage.removeItem('currentRole'); // Invalid role
            window.location.href = 'login.html';
            return;
        }
    }

    // 2. Apply UI Changes (Sidebar, Buttons)
    applyRoleBasedAccess(currentRole);

    // 3. Add Header Controls (Logout / Role Label)
    setupHeaderControls(currentRole, roleConfig.label);


    // --- Original Main.js Logic ---
    // Highlight Active Sidebar Item
    const navLinks = document.querySelectorAll('.nav-item');

    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPage || (currentPage === '' && href === 'index.html')) {
            link.classList.add('active');
            link.setAttribute('aria-current', 'page');
        }
    });

    // 15-minute inactivity timeout
    let _inactivityTimer;
    function _resetInactivityTimer() {
        clearTimeout(_inactivityTimer);
        _inactivityTimer = setTimeout(function () {
            window.logout();
        }, 15 * 60 * 1000);
    }
    ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(function (evt) {
        document.addEventListener(evt, _resetInactivityTimer, { passive: true });
    });
    _resetInactivityTimer();
});

function applyRoleBasedAccess(role) {
    const config = USER_ROLES[role];
    if (!config) return;

    // Sidebar Filtering
    const navItems = document.querySelectorAll('.nav-menu li a');
    navItems.forEach(item => {
        const href = item.getAttribute('href');
        if (!config.allowed_pages.includes(href)) {
            item.parentElement.style.display = 'none';
        } else {
            item.parentElement.style.display = 'block'; // Ensure visible on re-login
        }
    });

    // Inject "My Dashboard" and "Activity History" for patient role (persistent across all pages)
    if (role === 'patient') {
        const navMenu = document.querySelector('.nav-menu');
        if (navMenu && !navMenu.querySelector('a[href="patient_dashboard.html"]')) {
            const li = document.createElement('li');
            li.innerHTML = '<a href="patient_dashboard.html" class="nav-item"><span class="step-badge">3</span> My Dashboard</a>';
            navMenu.appendChild(li);
        }
        if (navMenu && !navMenu.querySelector('a[href="patient_activity.html"]')) {
            const li2 = document.createElement('li');
            li2.innerHTML = '<a href="patient_activity.html" class="nav-item"><span class="step-badge">4</span> Activity History</a>';
            navMenu.appendChild(li2);
        }
        if (navMenu && !navMenu.querySelector('a[href="hospital_load_status.html"]')) {
            const li3 = document.createElement('li');
            li3.innerHTML = '<a href="hospital_load_status.html" class="nav-item"><span class="step-badge">5</span> Hospital Load</a>';
            navMenu.appendChild(li3);
        }
        if (navMenu && !navMenu.querySelector('a[href="waiting_time_trend.html"]')) {
            const li4 = document.createElement('li');
            li4.innerHTML = '<a href="waiting_time_trend.html" class="nav-item"><span class="step-badge">6</span> Waiting Trend</a>';
            navMenu.appendChild(li4);
        }
    }

    // Inject nav items for doctor role
    if (role === 'doctor') {
        const navMenu = document.querySelector('.nav-menu');
        if (navMenu && !navMenu.querySelector('a[href="doctor_workload.html"]')) {
            const li = document.createElement('li');
            li.innerHTML = '<a href="doctor_workload.html" class="nav-item"><span class="step-badge">6</span> Doctor Workload</a>';
            navMenu.appendChild(li);
        }
        if (navMenu && !navMenu.querySelector('a[href="doctor_activity.html"]')) {
            const li2 = document.createElement('li');
            li2.innerHTML = '<a href="doctor_activity.html" class="nav-item"><span class="step-badge">7</span> Activity History</a>';
            navMenu.appendChild(li2);
        }
        if (navMenu && !navMenu.querySelector('a[href="doctor_dept_insights.html"]')) {
            const li3 = document.createElement('li');
            li3.innerHTML = '<a href="doctor_dept_insights.html" class="nav-item"><span class="step-badge">8</span> Dept Insights</a>';
            navMenu.appendChild(li3);
        }
        if (navMenu && !navMenu.querySelector('a[href="doctor_escalate.html"]')) {
            const li4 = document.createElement('li');
            li4.innerHTML = '<a href="doctor_escalate.html" class="nav-item"><span class="step-badge">9</span> Escalate Issue</a>';
            navMenu.appendChild(li4);
        }
    }

    // Inject nav items for staff role
    if (role === 'staff') {
        const navMenu = document.querySelector('.nav-menu');
        if (navMenu && !navMenu.querySelector('a[href="staff_panel.html"]')) {
            const li = document.createElement('li');
            li.innerHTML = '<a href="staff_panel.html" class="nav-item"><span class="step-badge">3</span> Staff Panel</a>';
            navMenu.appendChild(li);
        }
        if (navMenu && !navMenu.querySelector('a[href="staff_activity.html"]')) {
            const li2 = document.createElement('li');
            li2.innerHTML = '<a href="staff_activity.html" class="nav-item"><span class="step-badge">4</span> Recent Activity</a>';
            navMenu.appendChild(li2);
        }
        if (navMenu && !navMenu.querySelector('a[href="staff_allocation.html"]')) {
            const li3 = document.createElement('li');
            li3.innerHTML = '<a href="staff_allocation.html" class="nav-item"><span class="step-badge">5</span> AI Staff Allocation</a>';
            navMenu.appendChild(li3);
        }
        if (navMenu && !navMenu.querySelector('a[href="bottleneck_warnings.html"]')) {
            const li4 = document.createElement('li');
            li4.innerHTML = '<a href="bottleneck_warnings.html" class="nav-item"><span class="step-badge">6</span> Bottleneck Warnings</a>';
            navMenu.appendChild(li4);
        }
        if (navMenu && !navMenu.querySelector('a[href="patient_search.html"]')) {
            const li5 = document.createElement('li');
            li5.innerHTML = '<a href="patient_search.html" class="nav-item"><span class="step-badge">7</span> Patient Search</a>';
            navMenu.appendChild(li5);
        }
        if (navMenu && !navMenu.querySelector('a[href="escalate_issue.html"]')) {
            const li6 = document.createElement('li');
            li6.innerHTML = '<a href="escalate_issue.html" class="nav-item"><span class="step-badge">8</span> Escalate Issue</a>';
            navMenu.appendChild(li6);
        }
        if (navMenu && !navMenu.querySelector('a[href="department_performance.html"]')) {
            const li7 = document.createElement('li');
            li7.innerHTML = '<a href="department_performance.html" class="nav-item"><span class="step-badge">9</span> Dept. Performance</a>';
            navMenu.appendChild(li7);
        }
        if (navMenu && !navMenu.querySelector('a[href="department_insights.html"]')) {
            const li8 = document.createElement('li');
            li8.innerHTML = '<a href="department_insights.html" class="nav-item"><span class="step-badge">10</span> Dept. Insights</a>';
            navMenu.appendChild(li8);
        }
    }

    // Inject "Admin Center", "Notifications", "Escalations", and "Resources" for admin role (persistent across all pages)
    if (role === 'admin') {
        const navMenu = document.querySelector('.nav-menu');
        if (navMenu && !navMenu.querySelector('a[href="admin_dashboard.html"]')) {
            const li = document.createElement('li');
            li.innerHTML = '<a href="admin_dashboard.html" class="nav-item"><span class="step-badge">9</span> Admin Center</a>';
            navMenu.appendChild(li);
        }
        if (navMenu && !navMenu.querySelector('a[href="notification_center.html"]')) {
            const li2 = document.createElement('li');
            li2.innerHTML = '<a href="notification_center.html" class="nav-item"><span class="step-badge">10</span> Notifications</a>';
            navMenu.appendChild(li2);
        }
        if (navMenu && !navMenu.querySelector('a[href="escalation_reports.html"]')) {
            const li3 = document.createElement('li');
            li3.innerHTML = '<a href="escalation_reports.html" class="nav-item"><span class="step-badge">11</span> Escalations</a>';
            navMenu.appendChild(li3);
        }
        if (navMenu && !navMenu.querySelector('a[href="resource_allocation.html"]')) {
            const li4 = document.createElement('li');
            li4.innerHTML = '<a href="resource_allocation.html" class="nav-item"><span class="step-badge">12</span> Resources</a>';
            navMenu.appendChild(li4);
        }
    }

    // Specific Component Hiding (Modular Logic)
    // Add specific class checks if needed, e.g., <div class="rbac-admin-only">
    if (role !== 'admin') {
        document.querySelectorAll('.rbac-admin-only').forEach(el => el.style.display = 'none');
    }

    // Re-number all visible sidebar items sequentially
    renumberSidebar();
}

function renumberSidebar() {
    const navMenu = document.querySelector('.nav-menu');
    if (!navMenu) return;
    const allItems = navMenu.querySelectorAll('li');
    let visibleIndex = 1;
    allItems.forEach(li => {
        if (li.style.display === 'none') return;
        const badge = li.querySelector('.step-badge');
        if (badge) {
            badge.textContent = visibleIndex;
            visibleIndex++;
        }
    });
}

function setupHeaderControls(role, label) {
    const header = document.querySelector('header');
    if (!header) return;

    // Remove existing if any
    const existing = document.getElementById('rbac-controls');
    if (existing) existing.remove();

    const controls = document.createElement('div');
    controls.id = 'rbac-controls';
    controls.style.cssText = 'position: absolute; top: 1rem; right: 2rem; display: flex; align-items: center; gap: 1rem;';

    // Determine current theme icon (dark is default, .light-theme = light)
    const isLight = document.documentElement.classList.contains('light-theme');
    const themeIcon = isLight ? '<i class="fas fa-moon"></i>' : '<i class="fas fa-sun"></i>';
    const themeTitle = isLight ? 'Switch to dark mode' : 'Switch to light mode';

    controls.innerHTML = `
        <button id="theme-toggle-btn" onclick="toggleTheme()" title="${themeTitle}" aria-label="${themeTitle}">
            ${themeIcon}
        </button>
        <span style="font-size: 0.85rem; color: var(--text-muted);">Role: <strong>${label}</strong></span>
        <button id="logout-btn" onclick="window.logout()" aria-label="Logout" style="padding: 0.4rem 0.9rem; background: var(--primary-color); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 600; transition: background 0.2s;">
            <i class="fas fa-sign-out-alt"></i> Logout
        </button>
    `;

    // Make header relative if static
    if (getComputedStyle(header).position === 'static') {
        header.style.position = 'relative';
    }

    header.appendChild(controls);

    // Attach Event Listeners
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) logoutBtn.addEventListener('click', (e) => {
        // e.stopPropagation();
        window.logout();
    });
}

function navigateTo(page) {
    window.location.href = page;
}
