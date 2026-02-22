"""
PatientPath AI - WebSocket Router
=================================
WebSocket endpoint for real-time data streaming.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from services.occupancy_svc import OccupancyService
from services.metric_service import MetricService
from services.alert_service import AlertService
from utils.logger import get_logger
from config import settings

logger = get_logger(__name__)
router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_metadata: Dict[WebSocket, dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str = None):
        """Accept and track a new connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = {
            "client_id": client_id or f"client_{len(self.active_connections)}",
            "connected_at": datetime.now().isoformat(),
            "subscriptions": ["occupancy", "alerts"]  # Default subscriptions
        }
        logger.info(f"WebSocket connected: {self.connection_metadata[websocket]['client_id']}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            client_id = self.connection_metadata.get(websocket, {}).get("client_id", "unknown")
            del self.connection_metadata[websocket]
            logger.info(f"WebSocket disconnected: {client_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict, message_type: str = None):
        """Broadcast message to all connections."""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                # Check if client is subscribed to this message type
                subscriptions = self.connection_metadata.get(connection, {}).get("subscriptions", [])
                if message_type is None or message_type in subscriptions:
                    await connection.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    @property
    def connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Clients can connect to receive:
    - Occupancy updates
    - Alert notifications
    - Metric updates
    
    Message format:
    ```json
    {
        "type": "occupancy_update",
        "data": {...},
        "timestamp": "2024-01-15T10:30:00Z"
    }
    ```
    
    Client commands:
    - {"command": "subscribe", "topics": ["occupancy", "alerts"]}
    - {"command": "unsubscribe", "topics": ["alerts"]}
    - {"command": "ping"}
    """
    await manager.connect(websocket)
    
    try:
        # Send initial connection message
        await manager.send_personal_message({
            "type": "connection_established",
            "data": {
                "message": "Connected to PatientPath AI real-time feed",
                "client_id": manager.connection_metadata[websocket]["client_id"],
                "subscriptions": manager.connection_metadata[websocket]["subscriptions"]
            },
            "timestamp": datetime.now().isoformat()
        }, websocket)
        
        while True:
            # Wait for messages from client
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=settings.WEBSOCKET_HEARTBEAT
                )
                
                # Handle client commands
                command = data.get("command")
                
                if command == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                
                elif command == "subscribe":
                    topics = data.get("topics", [])
                    current_subs = manager.connection_metadata[websocket]["subscriptions"]
                    manager.connection_metadata[websocket]["subscriptions"] = list(
                        set(current_subs + topics)
                    )
                    await manager.send_personal_message({
                        "type": "subscribed",
                        "data": {"topics": topics},
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                
                elif command == "unsubscribe":
                    topics = data.get("topics", [])
                    current_subs = manager.connection_metadata[websocket]["subscriptions"]
                    manager.connection_metadata[websocket]["subscriptions"] = [
                        s for s in current_subs if s not in topics
                    ]
                    await manager.send_personal_message({
                        "type": "unsubscribed",
                        "data": {"topics": topics},
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                
                elif command == "get_status":
                    await manager.send_personal_message({
                        "type": "status",
                        "data": {
                            "connected_clients": manager.connection_count,
                            "your_subscriptions": manager.connection_metadata[websocket]["subscriptions"]
                        },
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                
                # Handle incoming data from Producer (detect.py)
                elif data.get("type") == "occupancy_update":
                    # Broadcast to all 'occupancy' subscribers
                    await manager.broadcast({
                        "type": "occupancy_update",
                        "data": data.get("data"),
                        "timestamp": datetime.now().isoformat()
                    }, message_type="occupancy")
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await manager.send_personal_message({
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat()
                }, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status."""
    return {
        "active_connections": manager.connection_count,
        "connections": [
            {
                "client_id": meta["client_id"],
                "connected_at": meta["connected_at"],
                "subscriptions": meta["subscriptions"]
            }
            for meta in manager.connection_metadata.values()
        ]
    }


# Helper function to broadcast updates from other parts of the application
async def broadcast_occupancy_update(data: dict):
    """Broadcast occupancy update to all connected clients."""
    await manager.broadcast({
        "type": "occupancy_update",
        "data": data,
        "timestamp": datetime.now().isoformat()
    }, message_type="occupancy")


async def broadcast_alert(data: dict):
    """Broadcast alert to all connected clients."""
    await manager.broadcast({
        "type": "alert",
        "data": data,
        "timestamp": datetime.now().isoformat()
    }, message_type="alerts")


async def broadcast_metric_update(data: dict):
    """Broadcast metric update to all connected clients."""
    await manager.broadcast({
        "type": "metric_update",
        "data": data,
        "timestamp": datetime.now().isoformat()
    }, message_type="metrics")
