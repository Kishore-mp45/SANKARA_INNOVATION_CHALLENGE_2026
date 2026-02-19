// Main.js - Shared Logic

// Removed by user request

window.logout = function () {
    localStorage.removeItem('currentRole');
    window.location.href = 'login.html';
}


// RBAC: Role Definitions
const USER_ROLES = {
    admin: {
        allowed_pages: ['index.html', 'occupancy.html', 'heatmap.html', 'metrics.html', 'alerts.html', 'charts.html', 'prediction.html', 'video.html', 'admin_dashboard.html', 'resource_allocation.html'],
        label: 'Administrator'
    },
    doctor: {
        allowed_pages: ['index.html', 'occupancy.html', 'heatmap.html', 'metrics.html', 'alerts.html', 'video.html'],
        label: 'Doctor'
    },
    staff: {
        allowed_pages: ['index.html', 'occupancy.html', 'heatmap.html', 'metrics.html', 'staff_panel.html'],
        label: 'Hospital Staff'
    },
    patient: {
        allowed_pages: ['index.html', 'occupancy.html', 'patient_dashboard.html'], // Added dashboard
        label: 'Patient'
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // 1. RBAC Check
    const currentRole = localStorage.getItem('currentRole');
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
            localStorage.removeItem('currentRole'); // Invalid role
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

    // Inject "My Dashboard" for patient role (persistent across all pages)
    if (role === 'patient') {
        const navMenu = document.querySelector('.nav-menu');
        if (navMenu && !navMenu.querySelector('a[href="patient_dashboard.html"]')) {
            const li = document.createElement('li');
            li.innerHTML = '<a href="patient_dashboard.html" class="nav-item"><span class="step-badge">3</span> My Dashboard</a>';
            navMenu.appendChild(li);
        }
    }

    // Inject "Admin Center" and "Resources" for admin role (persistent across all pages)
    if (role === 'admin') {
        const navMenu = document.querySelector('.nav-menu');
        if (navMenu && !navMenu.querySelector('a[href="admin_dashboard.html"]')) {
            const li = document.createElement('li');
            li.innerHTML = '<a href="admin_dashboard.html" class="nav-item"><span class="step-badge">10</span> Admin Center</a>';
            navMenu.appendChild(li);
        }
        if (navMenu && !navMenu.querySelector('a[href="resource_allocation.html"]')) {
            const li2 = document.createElement('li');
            li2.innerHTML = '<a href="resource_allocation.html" class="nav-item"><span class="step-badge">11</span> Resources</a>';
            navMenu.appendChild(li2);
        }
    }

    // Specific Component Hiding (Modular Logic)
    // Add specific class checks if needed, e.g., <div class="rbac-admin-only">
    if (role !== 'admin') {
        document.querySelectorAll('.rbac-admin-only').forEach(el => el.style.display = 'none');
    }
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

    // SVG now has pointer-events: none to prevent click swallowing
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
