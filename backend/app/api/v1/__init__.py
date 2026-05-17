from fastapi import APIRouter

from app.api.v1 import market, stocks, quotes, websocket

api_router = APIRouter()
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
api_router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
