/**
 * PatientPath AI - API Configuration
 * Auto-detects the backend URL based on the environment.
 * 
 * Local dev: Uses relative paths (same server serves frontend + backend)
 * Production: Set window.PATIENTPATH_API_URL or update PRODUCTION_API_URL below
 */

// Set this to your production backend URL after deploying (leave empty for local dev)
const PRODUCTION_API_URL = "";

// Auto-detect: use production URL if set, otherwise relative paths (local dev)
const API_BASE = PRODUCTION_API_URL || "";

// WebSocket URL (auto-detect protocol and host)
const WS_BASE = PRODUCTION_API_URL
    ? PRODUCTION_API_URL.replace(/^http/, 'ws')
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;
