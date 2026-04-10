"""
20-day average daily trading volume for Nifty 500 stocks.

Primary source: pre-fetched JSON file committed to the repo (avg_volume_20d.json).
Fallback: Yahoo Finance via yfinance (used only when running locally to refresh the cache).

The JSON file should be refreshed periodically by running this module directly:
    python historical_volume.py
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).resolve().parent / "data" / "avg_volume_20d.json"
_cache: Dict[str, float] = {}
_loaded: bool = False


def _load_cache() -> Dict[str, float]:
    """Load cached volume data from disk."""
    if not _CACHE_PATH.exists():
        return {}
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        volumes = data.get("volumes", {})
        cache_date = data.get("date", "unknown")
        logger.info(
            "Loaded 20D avg volumes from %s (%d symbols, dated %s)",
            _CACHE_PATH.name, len(volumes), cache_date,
        )
        return volumes
    except Exception as e:
        logger.warning("Failed to load volume cache: %s", e)
        return {}


def get_20d_avg_volumes(symbols: list[str] | None = None, force_refresh: bool = False) -> Dict[str, float]:
    """
    Get 20-day average volumes from the pre-fetched cache file.
    Always uses the committed JSON file — no runtime Yahoo calls on the server.
    """
    global _cache, _loaded

    if _loaded and _cache and not force_refresh:
        return _cache

    _cache = _load_cache()
    _loaded = True
    return _cache


# ---------------------------------------------------------------------------
# CLI: run locally to refresh the cache file
# ---------------------------------------------------------------------------
def _fetch_fresh(symbols: list[str]) -> Dict[str, float]:
    """Fetch 20-day avg volumes from Yahoo Finance. Run locally, not on server."""
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed — run: pip install yfinance")
        return {}

    volumes: Dict[str, float] = {}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=35)

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
                for sym in batch:
                    nse_sym = f"{sym}.NS"
                    try:
                        col = vol_data[nse_sym] if nse_sym in vol_data.columns else None
                        if col is not None:
                            last_20 = col.dropna().tail(20)
                            if len(last_20) > 0:
                                volumes[sym] = round(float(last_20.mean()), 0)
                    except Exception:
                        pass

            print(f"  Batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}: {len(volumes)} symbols")

        except Exception as e:
            print(f"  Batch error: {e}")
            continue

    return volumes


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from nifty500 import get_nifty500_symbols

    symbols = get_nifty500_symbols()
    print(f"\nFetching 20D avg volumes for {len(symbols)} symbols from Yahoo Finance...")
    volumes = _fetch_fresh(symbols)
    print(f"\n✅ Got volumes for {len(volumes)}/{len(symbols)} symbols")

    # Save
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "count": len(volumes),
            "volumes": volumes,
        }, f)
    print(f"Saved to {_CACHE_PATH}")

    # Show samples
    for sym in ["RELIANCE", "TCS", "WIPRO", "HDFCBANK", "INFY", "SBIN", "IRB"]:
        v = volumes.get(sym, 0)
        print(f"  {sym}: {v:,.0f}")
