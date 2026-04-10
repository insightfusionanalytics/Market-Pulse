"""
Fetch 20-day average daily trading volume for Nifty 500 stocks from Yahoo Finance.

Caches results in a JSON file and refreshes once per day.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).resolve().parent / "data" / "avg_volume_20d.json"
_cache: Dict[str, float] = {}
_cache_date: str = ""


def _load_cache() -> tuple[Dict[str, float], str]:
    """Load cached volume data from disk."""
    if not _CACHE_PATH.exists():
        return {}, ""
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("volumes", {}), data.get("date", "")
    except Exception:
        return {}, ""


def _save_cache(volumes: Dict[str, float], fetch_date: str) -> None:
    """Persist volume data to disk."""
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"date": fetch_date, "count": len(volumes), "volumes": volumes}, f)


def fetch_20d_avg_volumes(symbols: list[str]) -> Dict[str, float]:
    """
    Fetch 20-day average daily trading volume for a list of NSE symbols.
    Uses yfinance with .NS suffix for NSE stocks.
    Returns {symbol: avg_volume} dict.
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed — cannot fetch historical volumes")
        return {}

    volumes: Dict[str, float] = {}
    end_date = datetime.now()
    # Fetch ~35 calendar days to ensure we get 20 trading days
    start_date = end_date - timedelta(days=35)

    # Process in batches to avoid overwhelming Yahoo Finance
    batch_size = 50
    total = len(symbols)

    for i in range(0, total, batch_size):
        batch = symbols[i : i + batch_size]
        tickers = [f"{sym}.NS" for sym in batch]
        ticker_str = " ".join(tickers)

        try:
            data = yf.download(
                ticker_str,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                progress=False,
                threads=True,
            )

            if data.empty:
                continue

            # Handle single vs multi-ticker response
            if len(batch) == 1:
                vol_col = data.get("Volume")
                if vol_col is not None and not vol_col.empty:
                    last_20 = vol_col.dropna().tail(20)
                    if len(last_20) > 0:
                        volumes[batch[0]] = round(float(last_20.mean()), 0)
            else:
                vol_data = data.get("Volume")
                if vol_data is None:
                    continue
                for sym, ticker in zip(batch, tickers):
                    nse_sym = f"{sym}.NS"
                    try:
                        col = vol_data[nse_sym] if nse_sym in vol_data.columns else None
                        if col is not None:
                            last_20 = col.dropna().tail(20)
                            if len(last_20) > 0:
                                volumes[sym] = round(float(last_20.mean()), 0)
                    except Exception:
                        pass

            logger.info(f"Fetched volumes batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}: {len(volumes)} symbols so far")

        except Exception as e:
            logger.warning(f"yfinance batch error: {e}")
            continue

    logger.info(f"✅ Fetched 20-day avg volume for {len(volumes)}/{total} symbols")
    return volumes


def get_20d_avg_volumes(symbols: list[str], force_refresh: bool = False) -> Dict[str, float]:
    """
    Get 20-day average volumes, using cache if available and fresh (same day).
    """
    global _cache, _cache_date

    today = datetime.now().strftime("%Y-%m-%d")

    # Try in-memory cache first
    if _cache and _cache_date == today and not force_refresh:
        return _cache

    # Try disk cache
    disk_cache, disk_date = _load_cache()
    if disk_cache and disk_date == today and not force_refresh:
        _cache = disk_cache
        _cache_date = disk_date
        logger.info(f"Loaded 20D avg volumes from cache ({len(disk_cache)} symbols)")
        return _cache

    # Fetch fresh data
    logger.info("Fetching fresh 20-day avg volumes from Yahoo Finance...")
    volumes = fetch_20d_avg_volumes(symbols)

    if volumes:
        _cache = volumes
        _cache_date = today
        _save_cache(volumes, today)
    elif disk_cache:
        # Use stale cache if fresh fetch failed
        logger.warning("Fresh fetch failed, using stale cache")
        _cache = disk_cache
        _cache_date = disk_date

    return _cache
