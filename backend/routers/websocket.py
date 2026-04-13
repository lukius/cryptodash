from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


@router.websocket("/api/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    ws_manager = websocket.app.state.ws_manager
    connected = await ws_manager.connect(websocket, token)
    if not connected:
        return
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
