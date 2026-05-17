from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StockBase(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    exchange: Optional[str] = None


class StockInfo(StockBase):
    price: float
    change: float
    change_percent: float
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    volume: Optional[int] = None
    avg_volume: Optional[int] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    previous_close: Optional[float] = None


class OHLCV(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockHistory(BaseModel):
    symbol: str
    interval: str
    data: list[OHLCV]


class IndexData(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float


class QuoteData(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: Optional[int] = None
    timestamp: datetime
