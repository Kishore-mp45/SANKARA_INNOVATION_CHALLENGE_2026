// Main.js - Shared Logic

// Removed by user request

window.logout = function () {
    localStorage.removeItem('currentRole');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('currentDept');
    window.location.href = 'index.html';
}


// RBAC: Role Definitions
const USER_ROLES = {
    admin: {
        allowed_pages: ['occupancy.html', 'heatmap.html', 'metrics.html', 'alerts.html', 'charts.html', 'prediction.html', 'video.html', 'admin_dashboard.html', 'notification_center.html', 'escalation_reports.html', 'resource_allocation.html'],
        default_dashboard: 'admin_dashboard.html',
        label: 'Administrator'
    },
    doctor: {
        allowed_pages: ['occupancy.html', 'alerts.html', 'video.html', 'doctor_dashboard.html', 'doctor_workload.html', 'doctor_activity.html', 'doctor_dept_insights.html', 'doctor_escalate.html'],
        default_dashboard: 'doctor_dashboard.html',
        label: 'Doctor'
    },
    staff: {
        allowed_pages: ['occupancy.html', 'staff_panel.html', 'staff_activity.html', 'staff_allocation.html', 'bottleneck_warnings.html', 'patient_search.html', 'escalate_issue.html', 'department_performance.html', 'department_insights.html'],
        default_dashboard: 'staff_panel.html',
        label: 'Hospital Staff'
    },
    patient: {
        allowed_pages: ['patient_dashboard.html', 'live_navigator.html', 'patient_activity.html', 'hospital_load_status.html', 'waiting_time_trend.html'],
        default_dashboard: 'patient_dashboard.html',
        label: 'Patient'
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // 1. RBAC Check
    const currentRole = localStorage.getItem('currentRole');
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';

    // Skip check for login, signup, and landing pages
    if (currentPage === 'login.html' || currentPage === 'signup.html' || currentPage === 'index.html') return;

    if (!currentRole) {
        window.location.href = 'login.html';
        return;
    }

    const roleConfig = USER_ROLES[currentRole];

    // Redirect if role is invalid or page is not allowed
    if (!roleConfig || !roleConfig.allowed_pages.includes(currentPage)) {
        if (roleConfig && roleConfig.default_dashboard) {
            window.location.href = roleConfig.default_dashboard;
        } else {
            localStorage.removeItem('currentRole');
            window.location.href = 'login.html';
        }
        return;
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
        }
    });
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
        if (navMenu && !navMenu.querySelector('a[href="live_navigator.html"]')) {
            const liNav = document.createElement('li');
            liNav.innerHTML = '<a href="live_navigator.html" class="nav-item"><span class="step-badge">4</span> Live Navigator</a>';
            navMenu.appendChild(liNav);
        }
        if (navMenu && !navMenu.querySelector('a[href="patient_activity.html"]')) {
            const li2 = document.createElement('li');
            li2.innerHTML = '<a href="patient_activity.html" class="nav-item"><span class="step-badge">5</span> Activity History</a>';
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

    controls.innerHTML = `
        <div style="text-align: right;">
            <div style="font-size: 0.8rem; color: var(--text-muted);">Current Role</div>
            <div style="font-weight: 600; color: var(--primary-color);">${label}</div>
        </div>
        <button id="logout-btn" onclick="window.logout()" style="padding: 0.5rem 1rem; background: var(--card-bg); border: 1px solid var(--border-color); color: var(--text-color); border-radius: 6px; cursor: pointer; transition: all 0.2s;">
            Change Role
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
