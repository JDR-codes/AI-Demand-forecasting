# #fastapi+app/services/dashboard/dashboard_websocket_service.py
# """
# Dashboard WebSocket Service - Sends dashboard updates via WebSocket.
# """
# from datetime import datetime
# from sqlalchemy.orm import Session

# from fastapi_app.services.websocket.websocket_manager import manager
# from fastapi_app.services.dashboard.dashboard_service import DashboardService


# class DashboardWebSocketService:
#     """Service for sending dashboard updates via WebSocket."""
    
#     @staticmethod
#     async def broadcast_dashboard_update(db: Session):
#         """Broadcast dashboard updates to all connected clients."""
#         cards = DashboardService.get_dashboard_cards(db)
#         summary = DashboardService.get_summary(db)
        
#         await manager.send_to_channel("dashboard", {
#             "type": "dashboard_update",
#             "data": {
#                 "cards": cards,
#                 "summary": {
#                     "metrics": summary.metrics.dict() if hasattr(summary.metrics, 'dict') else summary.metrics,
#                     "timestamp": summary.timestamp.isoformat() if summary.timestamp else datetime.utcnow().isoformat()
#                 },
#                 "timestamp": datetime.utcnow().isoformat()
#             }
#         })