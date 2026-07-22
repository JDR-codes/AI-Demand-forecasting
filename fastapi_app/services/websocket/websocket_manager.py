# fastapi_app/services/websocket/websocket_manager.py
from typing import Dict, List, Set, Any, Optional
import json
import logging
from datetime import datetime
from fastapi import WebSocket
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket connection manager for real-time updates."""
    
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[int, WebSocket] = {}
        self.channel_subscriptions: Dict[str, List[int]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, channel: str = "dashboard", user_id: int = None):
        """Connect a WebSocket to a channel."""
        await websocket.accept()
        
        async with self._lock:
            if channel not in self.connections:
                self.connections[channel] = []
            self.connections[channel].append(websocket)
            
            if user_id:
                self.user_connections[user_id] = websocket
                if channel not in self.channel_subscriptions:
                    self.channel_subscriptions[channel] = []
                if user_id not in self.channel_subscriptions[channel]:
                    self.channel_subscriptions[channel].append(user_id)
        
        logger.info(f"WebSocket connected to channel: {channel}, user: {user_id}")
    
    def disconnect(self, websocket: WebSocket, channel: str = None, user_id: int = None):
        """Disconnect a WebSocket."""
        if channel and channel in self.connections:
            if websocket in self.connections[channel]:
                self.connections[channel].remove(websocket)
            if self.channel_subscriptions.get(channel) and user_id in self.channel_subscriptions[channel]:
                self.channel_subscriptions[channel].remove(user_id)
        
        if user_id and user_id in self.user_connections:
            del self.user_connections[user_id]
        
        logger.info(f"WebSocket disconnected from channel: {channel}, user: {user_id}")
    
    async def send_to_channel(self, channel: str, message: dict):
        """Send a message to all connections in a channel."""
        if channel not in self.connections:
            return
        
        data = json.dumps(message)
        disconnected = []
        
        for idx, connection in enumerate(self.connections[channel]):
            try:
                await connection.send_text(data)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                disconnected.append(idx)
        
        # Clean up disconnected connections
        if disconnected:
            async with self._lock:
                for idx in sorted(disconnected, reverse=True):
                    if idx < len(self.connections[channel]):
                        self.connections[channel].pop(idx)
    
    async def send_to_user(self, user_id: int, message: dict):
        """Send a message to a specific user."""
        if user_id not in self.user_connections:
            return
        
        try:
            await self.user_connections[user_id].send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send WebSocket message to user {user_id}: {e}")
            # Clean up disconnected connection
            if user_id in self.user_connections:
                del self.user_connections[user_id]
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connections."""
        data = json.dumps(message)
        for channel, connections in self.connections.items():
            disconnected = []
            for idx, connection in enumerate(connections):
                try:
                    await connection.send_text(data)
                except Exception as e:
                    logger.error(f"Failed to broadcast WebSocket message: {e}")
                    disconnected.append(idx)
            
            # Clean up disconnected connections
            if disconnected:
                async with self._lock:
                    for idx in sorted(disconnected, reverse=True):
                        if idx < len(self.connections[channel]):
                            self.connections[channel].pop(idx)
    
    async def send_progress_update(
        self,
        channel: str,
        job_id: str,
        progress: float,
        step: str,
        status: str,
        remaining_time: int = None,
        metadata: dict = None
    ):
        """Send a progress update."""
        message = {
            "type": "progress_update",
            "job_id": job_id,
            "progress": progress,
            "step": step,
            "status": status,
            "remaining_time": remaining_time,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_channel(channel, message)
    
    async def send_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        priority: str,
        entity_type: str = None,
        entity_id: str = None
    ):
        """Send a notification to a user."""
        data = {
            "type": "notification",
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "priority": priority,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(user_id, data)
    
    async def send_dashboard_update(self, data: dict):
        """Send a dashboard update."""
        message = {
            "type": "dashboard_update",
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_channel("dashboard", message)
    
    def get_connections_count(self) -> Dict[str, int]:
        """Get connection counts by channel."""
        return {channel: len(connections) for channel, connections in self.connections.items()}
    
    async def cleanup_inactive(self):
        """Clean up inactive WebSocket connections."""
        for channel, connections in list(self.connections.items()):
            active = []
            for conn in connections:
                try:
                    # Check if connection is still alive
                    await conn.send_text(json.dumps({"type": "ping"}))
                    active.append(conn)
                except Exception:
                    # Connection is dead, skip it
                    pass
            
            if len(active) != len(connections):
                async with self._lock:
                    self.connections[channel] = active
                logger.info(f"Cleaned up {len(connections) - len(active)} inactive connections from {channel}")

    # Add to fastapi_app/services/websocket/websocket_manager.py

    async def send_recommendation_update(self, data: dict):
        """Send recommendation update to all clients."""
        await self.broadcast_to_channel("recommendations", data)
    
    async def send_recommendation_progress(self, job_id: str, progress: float, step: str, status: str):
        """Send recommendation progress update."""
        await self.send_recommendation_update({
            "type": "recommendation_progress",
            "job_id": job_id,
            "progress": progress,
            "step": step,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def send_recommendation_completed(self, job_id: str, count: int):
        """Send recommendation completed update."""
        await self.send_recommendation_update({
            "type": "recommendation_completed",
            "job_id": job_id,
            "count": count,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def send_recommendation_executed(self, recommendation_id: int, sku: str):
        """Send recommendation executed update."""
        await self.send_recommendation_update({
            "type": "recommendation_executed",
            "id": recommendation_id,
            "sku": sku,
            "timestamp": datetime.utcnow().isoformat()
        })
# Global connection manager instance
manager = ConnectionManager()