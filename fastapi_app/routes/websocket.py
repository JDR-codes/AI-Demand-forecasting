#fastapi_app/routes/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
import logging
from datetime import datetime

from fastapi_app.services.websocket.websocket_manager import manager
from fastapi_app.db.session import SessionLocal
from fastapi_app.services.forecast.forecast_execution_service import ForecastExecutionService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    user_id: Optional[int] = Query(None)
):
    """WebSocket endpoint for user notifications."""
    await manager.connect(websocket, channel="notifications", user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.utcnow().isoformat()}))
                else:
                    await websocket.send_text(json.dumps({"status": "connected"}))
            except:
                await websocket.send_text(json.dumps({"status": "connected"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel="notifications", user_id=user_id)
        logger.info(f"WebSocket disconnected for user {user_id}")


@router.websocket("/ws/forecast/{job_id}")
async def websocket_forecast(
    websocket: WebSocket,
    job_id: str,
    user_id: Optional[int] = Query(None)
):
    """WebSocket endpoint for forecast job updates."""
    await manager.connect(websocket, channel=f"forecast_{job_id}", user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Send current status
            db = SessionLocal()
            try:
                status = ForecastExecutionService.get_live_status(db, job_id)
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "data": status
                }))
            finally:
                db.close()
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel=f"forecast_{job_id}", user_id=user_id)


@router.websocket("/ws/training/{job_id}")
async def websocket_training(
    websocket: WebSocket,
    job_id: str,
    user_id: Optional[int] = Query(None)
):
    """WebSocket endpoint for training job updates."""
    await manager.connect(websocket, channel=f"training_{job_id}", user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"status": "connected"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel=f"training_{job_id}", user_id=user_id)


@router.websocket("/ws/dashboard")
async def websocket_dashboard(
    websocket: WebSocket,
    user_id: Optional[int] = Query(None)
):
    """WebSocket endpoint for dashboard updates."""
    await manager.connect(websocket, channel="dashboard", user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"status": "connected"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel="dashboard", user_id=user_id)


@router.websocket("/ws/processing/{job_id}")
async def websocket_processing(
    websocket: WebSocket,
    job_id: str,
    user_id: Optional[int] = Query(None)
):
    """WebSocket endpoint for processing job updates."""
    await manager.connect(websocket, channel=f"processing_{job_id}", user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"status": "connected"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel=f"processing_{job_id}", user_id=user_id)


@router.websocket("/ws/uploads/{job_id}")
async def websocket_uploads(
    websocket: WebSocket,
    job_id: str,
    user_id: Optional[int] = Query(None)
):
    """WebSocket endpoint for upload job updates."""
    await manager.connect(websocket, channel=f"upload_{job_id}", user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"status": "connected"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel=f"upload_{job_id}", user_id=user_id)


@router.websocket("/ws/sync/{job_id}")
async def websocket_sync(
    websocket: WebSocket,
    job_id: str,
    user_id: Optional[int] = Query(None)
):
    """WebSocket endpoint for sync job updates."""
    await manager.connect(websocket, channel=f"sync_{job_id}", user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"status": "connected"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel=f"sync_{job_id}", user_id=user_id)