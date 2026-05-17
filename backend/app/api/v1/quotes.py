from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.schemas.stock import QuoteData, StockHistory
from app.services.yfinance_adapter import get_stock_info, get_stock_history

router = APIRouter()


@router.get("/{symbol}", response_model=QuoteData)
async def get_quote(symbol: str):
    """Get real-time quote for a stock."""
    info = await get_stock_info(symbol.upper())
    if not info:
        log.info(f"Quote for {symbol} not found")
        raise HTTPException(status_code=404, detail=f"Quote for {symbol} not found")

    return QuoteData(
        symbol=info["symbol"],
        price=info["price"],
        change=info["change"],
        change_percent=info["change_percent"],
        volume=info.get("volume"),
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/{symbol}/history", response_model=StockHistory)
async def get_history(
    symbol: str,
    interval: str = Query("1d", enum=["1d", "1wk", "1mo"]),
    range_: str = Query("1y", alias="range", enum=["1d", "1W", "1M", "3M", "1Y", "5Y", "MAX"]),
):
    """Get historical OHLCV data for charting."""
    data = await get_stock_history(symbol.upper(), interval, range_)
    if not data:
        raise HTTPException(status_code=404, detail=f"History for {symbol} not found")
    return data
