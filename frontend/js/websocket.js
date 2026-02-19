/**
 * Shared WebSocket Client for PatientPath AI
 * Handles connection, subscriptions, and event dispatching.
 */

const WS_URL = "ws://localhost:8000/ws";
let socket = null;
let reconnectTimer = null;

function connect() {
    console.log("Connecting to WebSocket...");
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        console.log("WebSocket Connected.");
        // Check for connection lost banner and remove it if present
        const banner = document.getElementById('connection-lost-banner');
        if (banner) banner.remove();

        // Subscribe to topics
        const subscribeMsg = {
            command: "subscribe",
            topics: ["occupancy", "alerts", "metrics"]
        };
        socket.send(JSON.stringify(subscribeMsg));
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
        console.warn("WebSocket Disconnected. Reconnecting in 3s...");
        showConnectionLost();
        socket = null;
        if (!reconnectTimer) {
            reconnectTimer = setTimeout(() => {
                reconnectTimer = null;
                connect();
            }, 3000);
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

function showConnectionLost() {
    if (document.getElementById('connection-lost-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'connection-lost-banner';
    banner.style.position = 'fixed';
    banner.style.top = '0';
    banner.style.left = '0';
    banner.style.width = '100%';
    banner.style.background = '#ef4444';
    banner.style.color = 'white';
    banner.style.textAlign = 'center';
    banner.style.padding = '0.5rem';
    banner.style.zIndex = '9999';
    banner.textContent = 'Realtime Connection Lost. Reconnecting...';
    document.body.prepend(banner);
}

// Start connection on load
window.addEventListener('load', connect);
