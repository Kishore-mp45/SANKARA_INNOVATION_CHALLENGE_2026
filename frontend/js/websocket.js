/**
 * Shared WebSocket Client for PatientPath AI
 * Handles connection, subscriptions, and event dispatching.
 */

const WS_URL = (typeof WS_BASE !== 'undefined' && WS_BASE) 
    ? WS_BASE + '/ws' 
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;
let socket = null;
let reconnectTimer = null;
let _reconnectAttempts = 0;
const _MAX_RECONNECT_ATTEMPTS = 10;
const _BASE_DELAY_MS = 3000;

function connect() {
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        console.log("WebSocket Connected.");
        _reconnectAttempts = 0; // Reset backoff counter on successful connection

        // Remove connection-lost banner if present
        const banner = document.getElementById('connection-lost-banner');
        if (banner) banner.remove();

        // Subscribe to topics
        socket.send(JSON.stringify({
            command: "subscribe",
            topics: ["occupancy", "alerts", "metrics"]
        }));
    };

    socket.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleMessage(msg);
        } catch (e) {
            console.error("Error parsing WebSocket message:", e);
        }
    };

    socket.onclose = () => {
        socket = null;
        if (_reconnectAttempts < _MAX_RECONNECT_ATTEMPTS) {
            const delay = Math.min(_BASE_DELAY_MS * Math.pow(1.5, _reconnectAttempts), 30000);
            _reconnectAttempts++;
            console.warn(`WebSocket disconnected. Reconnecting in ${Math.round(delay / 1000)}s (attempt ${_reconnectAttempts}/${_MAX_RECONNECT_ATTEMPTS})...`);
            showConnectionLost(false);
            if (!reconnectTimer) {
                reconnectTimer = setTimeout(() => {
                    reconnectTimer = null;
                    connect();
                }, delay);
            }
        } else {
            console.error("WebSocket: max reconnect attempts reached. Server may be offline.");
            showConnectionLost(true);
        }
    };

    socket.onerror = (error) => {
        console.error("WebSocket Error:", error);
    };
}

function handleMessage(msg) {
    // console.log("Received:", msg);

    if (msg.type === "occupancy_update") {
        // Dispatch custom event for pages to consume
        const event = new CustomEvent('occupancy-update', { detail: msg.data });
        document.dispatchEvent(event);
    } else if (msg.type === "alert") {
        const event = new CustomEvent('alert-new', { detail: msg.data });
        document.dispatchEvent(event);
    } else if (msg.type === "metric_update") {
        const event = new CustomEvent('metric-update', { detail: msg.data });
        document.dispatchEvent(event);
    }
}

function showConnectionLost(permanent) {
    let banner = document.getElementById('connection-lost-banner');
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'connection-lost-banner';
        banner.style.cssText = 'position:fixed;top:0;left:0;width:100%;background:#ef4444;color:white;text-align:center;padding:0.5rem;z-index:9999;font-size:0.9rem;';
        document.body.prepend(banner);
    }
    if (permanent) {
        banner.textContent = 'Server offline — realtime updates unavailable. Please refresh the page.';
    } else {
        banner.textContent = 'Realtime Connection Lost. Reconnecting...';
    }
}

// Start connection on load
window.addEventListener('load', connect);
