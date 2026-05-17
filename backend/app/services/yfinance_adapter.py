import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import random

logger = logging.getLogger(__name__)

# Thread pool for blocking yfinance calls
_executor = ThreadPoolExecutor(max_workers=4)

# In-memory cache
_cache = {}
_cache_time = {}
CACHE_TTL = 30  # seconds

# Enable fallback mode when Yahoo Finance is rate-limited / blocked
USE_FALLBACK = True


def _get_cached(key: str):
    now = datetime.utcnow()
    if key in _cache and (now - _cache_time.get(key, datetime.min)).total_seconds() < CACHE_TTL:
        return _cache[key]
    return None


def _set_cached(key: str, value):
    _cache[key] = value
    _cache_time[key] = datetime.utcnow()


def _safe_get(info: dict, keys: list, default=None):
    """Safely get first available key from dict."""
    for k in keys:
        if k in info and info[k] is not None:
            return info[k]
    return default


# ── Fallback Data (reasonable market prices) ─────────────

FALLBACK_STOCKS = {
    "AAPL":  {"price": 232.45, "change_pct": 1.25,  "name": "Apple Inc.", "sector": "Technology", "exchange": "NASDAQ", "market_cap": 3500000000000, "pe": 32.5, "vol": 45230000},
    "MSFT":  {"price": 441.78, "change_pct": -0.42, "name": "Microsoft Corporation", "sector": "Technology", "exchange": "NASDAQ", "market_cap": 3200000000000, "pe": 36.2, "vol": 22100000},
    "GOOGL": {"price": 176.32, "change_pct": -0.15, "name": "Alphabet Inc.", "sector": "Technology", "exchange": "NASDAQ", "market_cap": 2100000000000, "pe": 24.8, "vol": 18900000},
    "AMZN":  {"price": 198.54, "change_pct": 0.93,  "name": "Amazon.com Inc.", "sector": "Technology", "exchange": "NASDAQ", "market_cap": 2050000000000, "pe": 58.3, "vol": 31200000},
    "NVDA":  {"price": 138.25, "change_pct": 2.87,  "name": "NVIDIA Corporation", "sector": "Technology", "exchange": "NASDAQ", "market_cap": 3400000000000, "pe": 72.1, "vol": 285000000},
    "META":  {"price": 593.12, "change_pct": 0.67,  "name": "Meta Platforms Inc.", "sector": "Technology", "exchange": "NASDAQ", "market_cap": 1500000000000, "pe": 28.4, "vol": 15600000},
    "TSLA":  {"price": 248.87, "change_pct": -1.76, "name": "Tesla Inc.", "sector": "Automotive", "exchange": "NASDAQ", "market_cap": 800000000000, "pe": 68.5, "vol": 98200000},
    "JPM":   {"price": 245.33, "change_pct": 0.31,  "name": "JPMorgan Chase & Co.", "sector": "Financials", "exchange": "NYSE", "market_cap": 700000000000, "pe": 12.3, "vol": 8900000},
    "V":     {"price": 312.45, "change_pct": 0.55,  "name": "Visa Inc.", "sector": "Financials", "exchange": "NYSE", "market_cap": 650000000000, "pe": 30.1, "vol": 5400000},
    "JNJ":   {"price": 158.20, "change_pct": -0.12, "name": "Johnson & Johnson", "sector": "Healthcare", "exchange": "NYSE", "market_cap": 380000000000, "pe": 15.8, "vol": 6200000},
    "WMT":   {"price": 92.15,  "change_pct": 0.78,  "name": "Walmart Inc.", "sector": "Consumer Staples", "exchange": "NYSE", "market_cap": 740000000000, "pe": 26.4, "vol": 7200000},
    "PG":    {"price": 168.90, "change_pct": 0.22,  "name": "Procter & Gamble", "sector": "Consumer Staples", "exchange": "NYSE", "market_cap": 400000000000, "pe": 25.7, "vol": 5100000},
    "UNH":   {"price": 520.30, "change_pct": -0.45, "name": "UnitedHealth Group", "sector": "Healthcare", "exchange": "NYSE", "market_cap": 480000000000, "pe": 19.3, "vol": 3400000},
    "HD":    {"price": 358.75, "change_pct": 0.18,  "name": "Home Depot Inc.", "sector": "Consumer Discretionary", "exchange": "NYSE", "market_cap": 360000000000, "pe": 22.1, "vol": 2800000},
    "MA":    {"price": 478.20, "change_pct": 0.62,  "name": "Mastercard Inc.", "sector": "Financials", "exchange": "NYSE", "market_cap": 440000000000, "pe": 34.8, "vol": 2200000},
    "BAC":   {"price": 43.85,  "change_pct": 0.41,  "name": "Bank of America", "sector": "Financials", "exchange": "NYSE", "market_cap": 340000000000, "pe": 14.2, "vol": 28000000},
    "ABBV":  {"price": 198.50, "change_pct": 0.33,  "name": "AbbVie Inc.", "sector": "Healthcare", "exchange": "NYSE", "market_cap": 350000000000, "pe": 55.3, "vol": 4500000},
    "PFE":   {"price": 28.45,  "change_pct": -0.28, "name": "Pfizer Inc.", "sector": "Healthcare", "exchange": "NYSE", "market_cap": 160000000000, "pe": 72.5, "vol": 32000000},
    "KO":    {"price": 68.20,  "change_pct": 0.15,  "name": "Coca-Cola Co.", "sector": "Consumer Staples", "exchange": "NYSE", "market_cap": 295000000000, "pe": 24.1, "vol": 9800000},
    "NFLX":  {"price": 785.40, "change_pct": 1.12,  "name": "Netflix Inc.", "sector": "Technology", "exchange": "NASDAQ", "market_cap": 340000000000, "pe": 42.6, "vol": 3100000},
    "AMD":   {"price": 112.30, "change_pct": -0.85, "name": "Advanced Micro Devices", "sector": "Technology", "exchange": "NASDAQ", "market_cap": 180000000000, "pe": 148.2, "vol": 42000000},
    "INTC":  {"price": 22.15,  "change_pct": -1.45, "name": "Intel Corporation", "sector": "Technology", "exchange": "NASDAQ", "market_cap": 95000000000, "pe": None, "vol": 52000000},
    "CRM":   {"price": 285.60, "change_pct": 0.95,  "name": "Salesforce Inc.", "sector": "Technology", "exchange": "NYSE", "market_cap": 275000000000, "pe": 58.4, "vol": 4800000},
    "DIS":   {"price": 112.80, "change_pct": 0.42,  "name": "Walt Disney Co.", "sector": "Communication Services", "exchange": "NYSE", "market_cap": 205000000000, "pe": 22.8, "vol": 6800000},
}

FALLBACK_INDICES = {
    "SPX":  {"name": "S&P 500",      "price": 5842.91,  "change_pct": 0.74},
    "DJI":  {"name": "Dow Jones",    "price": 43725.38, "change_pct": 0.58},
    "IXIC": {"name": "Nasdaq",       "price": 19269.46, "change_pct": -0.23},
    "RUT":  {"name": "Russell 2000", "price": 2104.33,  "change_pct": 1.12},
}


def _fallback_stock_info(symbol: str) -> Optional[dict]:
    meta = FALLBACK_STOCKS.get(symbol.upper())
    if not meta:
        return None
    price = meta["price"]
    change_pct = meta["change_pct"]
    change = round(price * change_pct / 100, 2)
    return {
        "symbol": symbol.upper(),
        "name": meta["name"],
        "sector": meta["sector"],
        "exchange": meta["exchange"],
        "price": price,
        "change": change,
        "change_percent": change_pct,
        "market_cap": meta["market_cap"],
        "pe_ratio": meta["pe"],
        "fifty_two_week_low": round(price * 0.72, 2),
        "fifty_two_week_high": round(price * 1.28, 2),
        "volume": meta["vol"],
        "avg_volume": int(meta["vol"] * (0.8 + random.random() * 0.4)),
        "open": round(price * (1 - change_pct / 100 * 0.3), 2),
        "high": round(price * 1.008, 2),
        "low": round(price * 0.992, 2),
        "previous_close": round(price - change, 2),
    }


def _fallback_index_data() -> list[dict]:
    results = []
    for sym, meta in FALLBACK_INDICES.items():
        price = meta["price"]
        change_pct = meta["change_pct"]
        change = round(price * change_pct / 100, 2)
        results.append({
            "symbol": sym,
            "name": meta["name"],
            "price": price,
            "change": change,
            "change_percent": change_pct,
        })
    return results


def _generate_random_walk(start: float, steps: int, annual_vol: float = 0.25) -> list[float]:
    """Generate a plausible price random walk."""
    daily_vol = annual_vol / np.sqrt(252)
    prices = [start]
    for _ in range(steps - 1):
        prices.append(prices[-1] * (1 + np.random.normal(0, daily_vol)))
    return prices


def _fallback_history(symbol: str, interval: str = "1d", range_: str = "1y") -> Optional[dict]:
    meta = FALLBACK_STOCKS.get(symbol.upper())
    if not meta:
        return None

    period_map = {"1d": 1, "1W": 5, "1M": 30, "3M": 90, "1Y": 252, "5Y": 1260, "MAX": 2520}
    steps = period_map.get(range_, 252)

    end_price = meta["price"]
    prices = _generate_random_walk(end_price, steps)
    # Shift so last price matches current
    shift = end_price / prices[-1]
    prices = [p * shift for p in prices]

    records = []
    end_date = datetime.now()
    for i, price in enumerate(prices):
        date = end_date - timedelta(days=steps - 1 - i)
        daily_range = price * 0.015
        open_p = price * (1 + (random.random() - 0.5) * 0.005)
        high_p = max(open_p, price) + random.random() * daily_range
        low_p = min(open_p, price) - random.random() * daily_range
        records.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": round(open_p, 4),
            "high": round(high_p, 4),
            "low": round(low_p, 4),
            "close": round(price, 4),
            "volume": int(meta["vol"] * (0.5 + random.random())),
        })

    return {
        "symbol": symbol.upper(),
        "interval": interval,
        "data": records,
    }


# ── Popular stocks database for search ────────────────────

POPULAR_STOCKS = [
    {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology", "exchange": "NASDAQ"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology", "exchange": "NASDAQ"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology", "exchange": "NASDAQ"},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Technology", "exchange": "NASDAQ"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology", "exchange": "NASDAQ"},
    {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Technology", "exchange": "NASDAQ"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Automotive", "exchange": "NASDAQ"},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financials", "exchange": "NYSE"},
    {"symbol": "V", "name": "Visa Inc.", "sector": "Financials", "exchange": "NYSE"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare", "exchange": "NYSE"},
    {"symbol": "WMT", "name": "Walmart Inc.", "sector": "Consumer Staples", "exchange": "NYSE"},
    {"symbol": "PG", "name": "Procter & Gamble", "sector": "Consumer Staples", "exchange": "NYSE"},
    {"symbol": "UNH", "name": "UnitedHealth Group", "sector": "Healthcare", "exchange": "NYSE"},
    {"symbol": "HD", "name": "Home Depot Inc.", "sector": "Consumer Discretionary", "exchange": "NYSE"},
    {"symbol": "MA", "name": "Mastercard Inc.", "sector": "Financials", "exchange": "NYSE"},
    {"symbol": "BAC", "name": "Bank of America", "sector": "Financials", "exchange": "NYSE"},
    {"symbol": "ABBV", "name": "AbbVie Inc.", "sector": "Healthcare", "exchange": "NYSE"},
    {"symbol": "PFE", "name": "Pfizer Inc.", "sector": "Healthcare", "exchange": "NYSE"},
    {"symbol": "KO", "name": "Coca-Cola Co.", "sector": "Consumer Staples", "exchange": "NYSE"},
    {"symbol": "NFLX", "name": "Netflix Inc.", "sector": "Technology", "exchange": "NASDAQ"},
    {"symbol": "AMD", "name": "Advanced Micro Devices", "sector": "Technology", "exchange": "NASDAQ"},
    {"symbol": "INTC", "name": "Intel Corporation", "sector": "Technology", "exchange": "NASDAQ"},
    {"symbol": "CRM", "name": "Salesforce Inc.", "sector": "Technology", "exchange": "NYSE"},
    {"symbol": "DIS", "name": "Walt Disney Co.", "sector": "Communication Services", "exchange": "NYSE"},
]

INDICES = {
    "^GSPC": {"name": "S&P 500", "symbol": "SPX"},
    "^DJI": {"name": "Dow Jones", "symbol": "DJI"},
    "^IXIC": {"name": "Nasdaq", "symbol": "IXIC"},
    "^RUT": {"name": "Russell 2000", "symbol": "RUT"},
}


# ── Public API ────────────────────────────────────────────

async def get_stock_info(symbol: str) -> Optional[dict]:
    """Get stock info with caching. Falls back to static data if yfinance fails."""
    cache_key = f"info:{symbol}"
    if cached := _get_cached(cache_key):
        return cached

    def _fetch():
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            if not info:
                return None

            price = _safe_get(info, ["regularMarketPrice", "currentPrice", "previousClose"], 0.0)
            prev_close = _safe_get(info, ["regularMarketPreviousClose", "previousClose"], price)
            change = price - prev_close if price and prev_close else 0.0
            change_pct = (change / prev_close * 100) if prev_close else 0.0

            return {
                "symbol": symbol.upper(),
                "name": _safe_get(info, ["longName", "shortName"], symbol),
                "sector": _safe_get(info, ["sector", "industry"]),
                "exchange": _safe_get(info, ["exchange", "market"]),
                "price": round(price, 2) if price else 0.0,
                "change": round(change, 2),
                "change_percent": round(change_pct, 2),
                "market_cap": _safe_get(info, ["marketCap"]),
                "pe_ratio": _safe_get(info, ["trailingPE", "forwardPE"]),
                "fifty_two_week_low": _safe_get(info, ["fiftyTwoWeekLow"]),
                "fifty_two_week_high": _safe_get(info, ["fiftyTwoWeekHigh"]),
                "volume": _safe_get(info, ["regularMarketVolume", "volume"]),
                "avg_volume": _safe_get(info, ["averageVolume"]),
                "open": _safe_get(info, ["regularMarketOpen", "open"]),
                "high": _safe_get(info, ["regularMarketDayHigh", "dayHigh"]),
                "low": _safe_get(info, ["regularMarketDayLow", "dayLow"]),
                "previous_close": prev_close,
            }
        except Exception as e:
            logger.warning(f"yfinance error for {symbol}: {e}")
            return None

    result = await asyncio.get_event_loop().run_in_executor(_executor, _fetch)
    if result:
        _set_cached(cache_key, result)
        return result

    if USE_FALLBACK:
        fb = _fallback_stock_info(symbol)
        if fb:
            _set_cached(cache_key, fb)
            logger.info(f"Using fallback data for {symbol}")
        return fb
    return None


async def get_stock_history(symbol: str, interval: str = "1d", range_: str = "1y") -> Optional[dict]:
    """Get historical OHLCV data. Falls back to generated data if yfinance fails."""
    cache_key = f"history:{symbol}:{interval}:{range_}"
    if cached := _get_cached(cache_key):
        return cached

    def _fetch():
        try:
            period_map = {
                "1d": "1d", "1W": "5d", "1M": "1mo",
                "3M": "3mo", "1Y": "1y", "5Y": "5y", "MAX": "max"
            }
            period = period_map.get(range_, "1y")
            interval_map = {"1d": "1d", "1wk": "1wk", "1mo": "1mo"}
            yf_interval = interval_map.get(interval, "1d")

            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=yf_interval)

            if hist.empty:
                return None

            records = []
            for date, row in hist.iterrows():
                records.append({
                    "date": date.strftime("%Y-%m-%d") if isinstance(date, pd.Timestamp) else str(date),
                    "open": round(float(row["Open"]), 4),
                    "high": round(float(row["High"]), 4),
                    "low": round(float(row["Low"]), 4),
                    "close": round(float(row["Close"]), 4),
                    "volume": int(row["Volume"]),
                })

            return {
                "symbol": symbol.upper(),
                "interval": interval,
                "data": records,
            }
        except Exception as e:
            logger.warning(f"yfinance history error for {symbol}: {e}")
            return None

    result = await asyncio.get_event_loop().run_in_executor(_executor, _fetch)
    if result:
        _set_cached(cache_key, result)
        return result

    if USE_FALLBACK:
        fb = _fallback_history(symbol, interval, range_)
        if fb:
            _set_cached(cache_key, fb)
            logger.info(f"Using fallback history for {symbol}")
        return fb
    return None


async def get_index_data() -> list[dict]:
    """Get major US indices. Falls back to static data if yfinance fails."""
    cache_key = "indices"
    if cached := _get_cached(cache_key):
        return cached

    results = []

    def _fetch_index(yf_symbol, meta):
        try:
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="2d", interval="1d")
            if hist.empty or len(hist) < 1:
                return None

            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else latest

            price = float(latest["Close"])
            prev_close = float(prev["Close"])
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            return {
                "symbol": meta["symbol"],
                "name": meta["name"],
                "price": round(price, 2),
                "change": round(change, 2),
                "change_percent": round(change_pct, 2),
            }
        except Exception as e:
            logger.warning(f"Index fetch error for {yf_symbol}: {e}")
            return None

    tasks = []
    for yf_sym, meta in INDICES.items():
        tasks.append(asyncio.get_event_loop().run_in_executor(
            _executor, _fetch_index, yf_sym, meta
        ))

    fetched = await asyncio.gather(*tasks)
    for item in fetched:
        if item:
            results.append(item)

    if results:
        _set_cached(cache_key, results)
        return results

    if USE_FALLBACK:
        fb = _fallback_index_data()
        _set_cached(cache_key, fb)
        logger.info("Using fallback index data")
        return fb
    return []


async def search_stocks(query: str) -> list[dict]:
    """Search stocks by symbol or name."""
    query = query.upper().strip()
    if not query:
        return POPULAR_STOCKS[:12]

    results = []
    for stock in POPULAR_STOCKS:
        if query in stock["symbol"] or query in stock["name"].upper():
            results.append(stock)

    # Also try to get info if exact symbol match
    if len(results) == 0 and len(query) <= 5:
        info = await get_stock_info(query)
        if info:
            results.append({
                "symbol": info["symbol"],
                "name": info["name"],
                "sector": info.get("sector"),
                "exchange": info.get("exchange"),
            })

    return results[:20]


async def get_batch_quotes(symbols: list[str]) -> list[dict]:
    """Get quotes for multiple symbols efficiently."""
    tasks = [get_stock_info(sym) for sym in symbols]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r]
