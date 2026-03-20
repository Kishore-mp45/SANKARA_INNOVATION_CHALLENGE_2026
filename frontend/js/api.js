/**
 * PatientPath AI - Shared API Client
 * Provides consistent API calling utilities across all pages.
 * Depends on config.js being loaded first (for API_BASE).
 */

(function () {
    'use strict';

    window.AppAPI = {
        /** GET request with JSON response */
        get: async function (path) {
            var base = (typeof API_BASE !== 'undefined') ? API_BASE : '';
            var res = await fetch(base + path);
            if (!res.ok) {
                var err = await res.json().catch(function () { return { detail: 'Request failed' }; });
                throw { status: res.status, detail: err.detail || 'Request failed' };
            }
            return res.json();
        },

        /** POST request with JSON body and response */
        post: async function (path, body) {
            var base = (typeof API_BASE !== 'undefined') ? API_BASE : '';
            var res = await fetch(base + path, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok) {
                throw { status: res.status, detail: data.detail || 'Request failed', data: data };
            }
            return data;
        },

        /** Department display name mapping */
        DEPT_DISPLAY: {
            registration: 'Registration',
            consultation: 'Consultation',
            diagnostics: 'Diagnostics',
            vision_lab: 'Vision Lab',
            dilation_hall: 'Dilation Hall',
            pharmacy: 'Pharmacy',
            billing_insurance: 'Billing & Insurance',
        },

        /** Get display name for a department key */
        deptName: function (key) {
            return this.DEPT_DISPLAY[key] || key;
        },
    };
})();
