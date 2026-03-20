/**
 * PatientPath AI - Shared Auth/Session Utilities
 * Provides consistent session access across all pages.
 */

(function () {
    'use strict';

    window.AppAuth = {
        /** Get current user session data */
        getSession: function () {
            return {
                role: localStorage.getItem('currentRole'),
                user: localStorage.getItem('currentUser'),         // generated_id
                userId: localStorage.getItem('currentUserId'),     // numeric DB id
                username: localStorage.getItem('currentUsername'),
                mobile: localStorage.getItem('currentMobile'),
                dept: localStorage.getItem('currentDept'),
                patientId: localStorage.getItem('currentPatientId'),
            };
        },

        /** Check if user is logged in with a specific role */
        isRole: function (role) {
            return localStorage.getItem('currentRole') === role;
        },

        /** Check if user is logged in at all */
        isLoggedIn: function () {
            return !!localStorage.getItem('currentRole') && !!localStorage.getItem('currentUser');
        },

        /** Clear session and redirect to login */
        logout: function () {
            localStorage.removeItem('currentRole');
            localStorage.removeItem('currentUser');
            localStorage.removeItem('currentUserId');
            localStorage.removeItem('currentUsername');
            localStorage.removeItem('currentMobile');
            localStorage.removeItem('currentDept');
            localStorage.removeItem('currentPatientId');
            window.location.href = 'login.html';
        },

        /** Get check-in target department from URL params (used by login page) */
        getCheckinTarget: function () {
            var params = new URLSearchParams(window.location.search);
            return params.get('checkin_dept') || null;
        },
    };
})();
