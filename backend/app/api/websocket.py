from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.websocket_manager import manager

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/progress")
async def websocket_progress(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
