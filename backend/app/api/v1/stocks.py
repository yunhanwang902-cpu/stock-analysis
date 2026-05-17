from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.schemas.stock import StockBase, StockInfo
from app.services.yfinance_adapter import search_stocks, get_stock_info, POPULAR_STOCKS

router = APIRouter()


@router.get("/search", response_model=List[StockBase])
async def search(
    q: str = Query(..., min_length=1, max_length=20, description="Search query"),
):
    """Search stocks by symbol or company name."""
    results = await search_stocks(q)
    return results


@router.get("/trending", response_model=List[StockBase])
async def trending():
    """Get trending/popular stocks."""
    return POPULAR_STOCKS[:12]


@router.get("/{symbol}", response_model=StockInfo)
async def stock_detail(symbol: str):
    """Get detailed stock information."""
    info = await get_stock_info(symbol.upper())
    if not info:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    return info
