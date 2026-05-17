from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import logging

from app.services.yfinance_adapter import get_batch_quotes

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.subscriptions: dict[str, set[str]] = {}  # symbol -> {client_ids}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
        # Remove from all subscriptions
        for symbol, clients in list(self.subscriptions.items()):
            clients.discard(client_id)
            if not clients:
                del self.subscriptions[symbol]
        logger.info(f"Client {client_id} disconnected")

    def subscribe(self, client_id: str, symbols: list[str]):
        for symbol in symbols:
            self.subscriptions.setdefault(symbol.upper(), set()).add(client_id)
        logger.info(f"Client {client_id} subscribed to {symbols}")

    def unsubscribe(self, client_id: str, symbols: list[str]):
        for symbol in symbols:
            if symbol.upper() in self.subscriptions:
                self.subscriptions[symbol.upper()].discard(client_id)

    async def broadcast_to_subscribers(self, symbol: str, data: dict):
        clients = self.subscriptions.get(symbol.upper(), set())
        if not clients:
            return
        message = json.dumps({"type": "quote", "data": data})
        dead_clients = []
        for client_id in clients:
            ws = self.active_connections.get(client_id)
            if ws:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead_clients.append(client_id)
            else:
                dead_clients.append(client_id)
        # Cleanup dead connections
        for cid in dead_clients:
            self.disconnect(cid)


manager = ConnectionManager()


async def broadcast_loop():
    """Background task: fetch and broadcast quotes every 10s."""
    while True:
        await asyncio.sleep(10)
        if not manager.subscriptions:
            continue

        symbols = list(manager.subscriptions.keys())
        try:
            quotes = await get_batch_quotes(symbols)
            for quote in quotes:
                await manager.broadcast_to_subscribers(
                    quote["symbol"],
                    {
                        "symbol": quote["symbol"],
                        "price": quote["price"],
                        "change": quote["change"],
                        "change_percent": quote["change_percent"],
                        "volume": quote.get("volume"),
                    }
                )
        except Exception as e:
            logger.warning(f"Broadcast loop error: {e}")


@router.websocket("/quotes")
async def websocket_endpoint(websocket: WebSocket):
    client_id = f"{id(websocket)}"
    await manager.connect(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")

                if msg_type == "subscribe":
                    symbols = msg.get("symbols", [])
                    manager.subscribe(client_id, symbols)
                    # Send immediate snapshot
                    quotes = await get_batch_quotes(symbols)
                    await websocket.send_text(json.dumps({
                        "type": "snapshot",
                        "data": quotes,
                    }))

                elif msg_type == "unsubscribe":
                    symbols = msg.get("symbols", [])
                    manager.unsubscribe(client_id, symbols)

                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        manager.disconnect(client_id)
