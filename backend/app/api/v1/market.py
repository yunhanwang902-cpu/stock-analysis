from fastapi import APIRouter, HTTPException
from typing import List

from app.schemas.stock import IndexData
from app.services.yfinance_adapter import get_index_data

router = APIRouter()


@router.get("/indices", response_model=List[IndexData])
async def market_indices():
    """Get major US market indices."""
    data = await get_index_data()
    if not data:
        raise HTTPException(status_code=503, detail="Market data temporarily unavailable")
    return data
