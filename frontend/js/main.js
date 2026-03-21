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
        allowed_pages: ['occupancy.html', 'heatmap.html', 'metrics.html', 'alerts.html', 'charts.html', 'prediction.html', 'video.html', 'admin_dashboard.html', 'notification_center.html', 'escalation_reports.html', 'resource_allocation.html', 'staff_confirmation.html', 'movement_audit.html'],
        default_dashboard: 'admin_dashboard.html',
        label: 'Administrator'
    },
    doctor: {
        allowed_pages: ['occupancy.html', 'alerts.html', 'video.html', 'doctor_dashboard.html', 'doctor_workload.html', 'doctor_activity.html', 'doctor_dept_insights.html', 'doctor_escalate.html'],
        default_dashboard: 'doctor_dashboard.html',
        label: 'Doctor'
    },
    staff: {
        allowed_pages: ['occupancy.html', 'staff_panel.html', 'staff_activity.html', 'staff_allocation.html', 'bottleneck_warnings.html', 'patient_search.html', 'escalate_issue.html', 'department_performance.html', 'department_insights.html', 'qr_scanner.html', 'staff_confirmation.html'],
        default_dashboard: 'qr_scanner.html',
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

    // Skip check for login, signup, landing, and admin bridge pages
    if (currentPage === 'login.html' || currentPage === 'signup.html' || currentPage === 'index.html' || currentPage === 'admin_login.html' || currentPage === 'admin_bridge.html') return;

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

    // 2b. Make sidebar brand clickable -> project info page
    const brandEl = document.querySelector('.sidebar .brand');
    if (brandEl) {
        brandEl.style.cursor = 'pointer';
        brandEl.title = 'Project Info';
        brandEl.addEventListener('click', function() { window.location.href = 'index.html'; });
    }

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

    // Fixed nav order per role - clear and rebuild to ensure consistency across all pages
    const NAV_ITEMS = {
        patient: [
            { href: 'patient_dashboard.html', label: 'My Dashboard' },
            { href: 'live_navigator.html', label: 'Live Navigator' },
            { href: 'patient_activity.html', label: 'Activity History' },
            { href: 'hospital_load_status.html', label: 'Hospital Load' },
            { href: 'waiting_time_trend.html', label: 'Waiting Trend' },
        ],
        doctor: [
            { href: 'occupancy.html', label: 'Live Occupancy' },
            { href: 'video.html', label: 'Live Video' },
            { href: 'alerts.html', label: 'Alerts' },
            { href: 'doctor_dashboard.html', label: 'Doctor Panel' },
            { href: 'doctor_workload.html', label: 'Doctor Workload' },
            { href: 'doctor_activity.html', label: 'Activity History' },
            { href: 'doctor_dept_insights.html', label: 'Dept Insights' },
            { href: 'doctor_escalate.html', label: 'Escalate Issue' },
        ],
        staff: [
            { href: 'occupancy.html', label: 'Live Occupancy' },
            { href: 'qr_scanner.html', label: 'QR Scanner & Actions' },
            { href: 'staff_confirmation.html', label: 'Confirm Queue' },
            { href: 'staff_activity.html', label: 'Recent Activity' },
            { href: 'staff_allocation.html', label: 'AI Staff Allocation' },
            { href: 'bottleneck_warnings.html', label: 'Bottleneck Warnings' },
            { href: 'patient_search.html', label: 'Patient Search' },
            { href: 'escalate_issue.html', label: 'Escalate Issue' },
            { href: 'department_performance.html', label: 'Dept. Performance' },
            { href: 'department_insights.html', label: 'Dept. Insights' },
        ],
        admin: [
            { href: 'occupancy.html', label: 'Live Occupancy' },
            { href: 'heatmap.html', label: 'Zone Heatmap' },
            { href: 'staff_confirmation.html', label: 'Confirm Queue' },
            { href: 'movement_audit.html', label: 'Movement Audit' },
            { href: 'metrics.html', label: 'Metrics' },
            { href: 'alerts.html', label: 'Alerts' },
            { href: 'charts.html', label: 'Charts' },
            { href: 'prediction.html', label: 'Prediction' },
            { href: 'video.html', label: 'Live Video' },
            { href: 'admin_dashboard.html', label: 'Admin Center' },
            { href: 'notification_center.html', label: 'Notifications' },
            { href: 'escalation_reports.html', label: 'Escalations' },
            { href: 'resource_allocation.html', label: 'Resources' },
        ],
    };

    const navMenu = document.querySelector('.nav-menu');
    if (navMenu && NAV_ITEMS[role]) {
        const currentPage = window.location.pathname.split('/').pop() || '';
        navMenu.innerHTML = '';
        NAV_ITEMS[role].forEach(function (item, idx) {
            const li = document.createElement('li');
            const isActive = (item.href === currentPage) ? ' active' : '';
            li.innerHTML = '<a href="' + item.href + '" class="nav-item' + isActive + '"><span class="step-badge">' + (idx + 1) + '</span> ' + item.label + '</a>';
            navMenu.appendChild(li);
        });
    }

    // Specific Component Hiding (Modular Logic)
    if (role !== 'admin') {
        document.querySelectorAll('.rbac-admin-only').forEach(el => el.style.display = 'none');
    }
}

function getInitials(name) {
    if (!name) return '?';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
}

window.toggleProfileDropdown = function() {
    const dd = document.getElementById('profile-dropdown');
    if (dd) {
        dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
    }
};

// Close profile dropdown when clicking outside
document.addEventListener('click', function(e) {
    const dd = document.getElementById('profile-dropdown');
    const icon = document.getElementById('profile-icon');
    if (dd && icon && !icon.contains(e.target)) {
        dd.style.display = 'none';
    }
});

function setupHeaderControls(role, label) {
    const header = document.querySelector('header');
    if (!header) return;

    // Remove existing if any
    const existing = document.getElementById('rbac-controls');
    if (existing) existing.remove();

    const controls = document.createElement('div');
    controls.id = 'rbac-controls';
    controls.style.cssText = 'position: absolute; top: 1rem; right: 2rem; display: flex; align-items: center; gap: 1rem;';

    const username = localStorage.getItem('currentUsername') || 'User';
    const generatedId = localStorage.getItem('currentUser') || '';
    const mobile = localStorage.getItem('currentMobile') || '';
    const dept = localStorage.getItem('currentDept') || '';
    const initials = getInitials(username);

    const deptLine = dept ? `<div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.15rem;"><i class="fas fa-building" style="width:14px;"></i> ${dept.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</div>` : '';
    const mobileLine = mobile ? `<div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.15rem;"><i class="fas fa-phone" style="width:14px;"></i> ${mobile}</div>` : '';

    const apiBase = (typeof API_BASE !== 'undefined') ? API_BASE : '';
    const qrSection = role === 'patient' ? `
                <div id="profile-qr-section" style="border-top:1px solid var(--border-color); padding-top:0.75rem; margin-top:0.5rem; text-align:center;">
                    <div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.5rem;"><i class="fas fa-qrcode"></i> My QR Code</div>
                    <div style="background:#fff; border-radius:8px; padding:8px; display:inline-block;">
                        <img id="profile-qr-img" src="${apiBase}/auth/qr-code/${generatedId}" alt="QR Code" style="width:140px; height:140px; display:block;" onerror="this.parentElement.parentElement.style.display='none'">
                    </div>
                    <div style="font-size:0.7rem; color:var(--text-muted); margin-top:0.4rem;">Show this to staff for scanning</div>
                </div>` : '';

    controls.innerHTML = `
        <div id="theme-toggle-container" style="display: flex; align-items: center;"></div>
        <div id="profile-icon" style="cursor:pointer; position:relative;" onclick="window.toggleProfileDropdown()">
            <div style="width:42px; height:42px; border-radius:50%; background:var(--primary-color); display:flex; align-items:center; justify-content:center; color:white; font-weight:700; font-size:0.95rem; letter-spacing:0.5px; user-select:none; transition:transform 0.2s;" onmouseover="this.style.transform='scale(1.08)'" onmouseout="this.style.transform='scale(1)'">
                ${initials}
            </div>
            <div id="profile-dropdown" style="display:none; position:absolute; right:0; top:52px; background:var(--sidebar-bg); border:1px solid var(--border-color); border-radius:12px; padding:1.25rem; min-width:260px; z-index:99999; box-shadow:0 12px 32px rgba(0,0,0,0.3);">
                <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:0.75rem;">
                    <div style="width:44px; height:44px; border-radius:50%; background:var(--primary-color); display:flex; align-items:center; justify-content:center; color:white; font-weight:700; font-size:1rem; flex-shrink:0;">${initials}</div>
                    <div>
                        <div style="font-weight:700; color:var(--text-main); font-size:0.95rem;">${username}</div>
                        <div style="font-size:0.8rem; color:var(--primary-color); font-weight:600;">${generatedId}</div>
                    </div>
                </div>
                <div style="border-top:1px solid var(--border-color); padding-top:0.75rem; margin-bottom:0.5rem;">
                    <div style="font-size:0.8rem; color:var(--text-muted); margin-bottom:0.15rem;"><i class="fas fa-user-tag" style="width:14px;"></i> ${label}</div>
                    ${deptLine}
                    ${mobileLine}
                </div>
                ${qrSection}
                <button onclick="window.logout()" style="width:100%; padding:0.55rem; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.25); color:#ef4444; border-radius:8px; cursor:pointer; font-weight:600; font-size:0.85rem; transition:all 0.2s; margin-top:0.5rem;" onmouseover="this.style.background='#ef4444';this.style.color='#fff'" onmouseout="this.style.background='rgba(239,68,68,0.1)';this.style.color='#ef4444'">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </button>
            </div>
        </div>
    `;

    // Make header relative if static
    if (getComputedStyle(header).position === 'static') {
        header.style.position = 'relative';
    }

    header.appendChild(controls);

    // Move the global theme toggle inside the container cleanly
    const moveToggle = () => {
        const toggleBtn = document.getElementById('global-theme-toggle');
        const container = document.getElementById('theme-toggle-container');
        if (toggleBtn && container && toggleBtn.parentNode !== container) {
            // Override fixed styles to fit smoothly inside the header
            Object.assign(toggleBtn.style, {
                position: 'relative',
                top: 'auto',
                right: 'auto',
                zIndex: 'auto',
                width: '38px',
                height: '38px',
                fontSize: '1rem',
                boxShadow: 'none'
            });
            container.appendChild(toggleBtn);
            return true;
        }
        return false;
    };

    // If the toggle already exists, move it. Otherwise wait for it to be injected by theme.js.
    if (!moveToggle()) {
        const observer = new MutationObserver((mutations, obs) => {
            if (moveToggle()) {
                obs.disconnect();
            }
        });
        observer.observe(document.body, { childList: true, subtree: false });
    }
}

function navigateTo(page) {
    window.location.href = page;
}
