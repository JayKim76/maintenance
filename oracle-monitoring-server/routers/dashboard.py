from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.monitoring import MonitoringService
import asyncio
import json

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
service = MonitoringService()

@router.get("/metrics")
async def get_metrics():
    return await service.get_dashboard_data()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await service.get_dashboard_data()
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(2) # Update every 2 seconds
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")
        await websocket.close()
