from __future__ import annotations

"""
Pre-Open Scanner - FastAPI application entry point.

Real-time stock market pre-open scanner backend.
Data source: Pradeep Ji's Redis DB (replaces Fyers WebSocket).
"""

import asyncio
import csv
import io
import json
import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from auth import create_access_token, get_current_user, verify_token
from redis_feed import RedisDataFeed          # ← replaces FyersDataFeed
from models import LoginRequest
from nifty500 import get_nifty500_symbols
from shortlist_engine import BaselineStore, evaluate_and_rank, merge_rules

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)
load_dotenv(Path(__file__).resolve().parent / ".env", override=False)

_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"
_config: dict = {}
if _CONFIG_PATH.exists():
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f) or {}

def get_config() -> dict:
    return _config


_DAILY_FINAL_DIR = _PROJECT_ROOT / "backend" / "data" / "daily_final"
_DAILY_FINAL_DIR.mkdir(parents=True, exist_ok=True)

_scheduler: AsyncIOScheduler | None = None

_shortlist_rules = merge_rules(_config.get("shortlist_rules", {}))
_baseline_store = BaselineStore(
    store_path=_PROJECT_ROOT / "backend" / "data" / "preopen_baseline.json",
    lookback_days=int(_shortlist_rules.get("lookback_days", 20)),
)
_frozen_shortlist: list[dict] = []
_frozen_stocks: list[dict] = []

_scanner_cfg = _config.get("scanner", {})
_preopen_freeze_at = str(_scanner_cfg.get("freeze_at", "09:08:00"))
_dashboard_refresh_seconds = int(_scanner_cfg.get("dashboard_refresh_seconds", 5))
if _dashboard_refresh_seconds < 1:
    _dashboard_refresh_seconds = 5
if os.getenv("DASHBOARD_REFRESH_SECONDS"):
    try:
        _dashboard_refresh_seconds = max(1, int(os.getenv("DASHBOARD_REFRESH_SECONDS", "5")))
    except ValueError:
        _dashboard_refresh_seconds = 5


def _evaluate_stocks(stocks: list[dict]) -> tuple[list[dict], list[dict]]:
    return evaluate_and_rank(
        stocks=stocks,
        baseline_store=_baseline_store,
        rules=_shortlist_rules,
        now_day=date.today().isoformat(),
    )


def _resolve_dashboard_window(stocks: list[dict], shortlist: list[dict]) -> tuple[list[dict], list[dict], bool, str | None]:
    global _frozen_stocks, _frozen_shortlist

    now = datetime.now().strftime("%H:%M:%S")
    if "09:00:00" <= now <= _preopen_freeze_at:
        _frozen_stocks = []
        _frozen_shortlist = []
        return stocks, shortlist, False, None

    if now > _preopen_freeze_at:
        if not _frozen_stocks:
            _frozen_stocks = list(stocks)
        if not _frozen_shortlist:
            _frozen_shortlist = list(shortlist)
        return _frozen_stocks, _frozen_shortlist, True, f"Dashboard frozen at {_preopen_freeze_at} IST"

    return stocks, shortlist, False, None

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("PreOpenScanner")

# ---------------------------------------------------------------------------
# App and state
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Pre-Open Scanner",
    description="Real-time NSE pre-open scanner — powered by Redis data feed",
    version="2.0.0",
)

feed: RedisDataFeed | None = None
ws_clients: set[WebSocket] = set()
_broadcast_task: asyncio.Task | None = None

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
_cors_origins = _config.get("cors", {}).get("origins", [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://pre-open-scanner.lovable.app",
    "https://scanner.insightfusionanalytics.com",
])
_cors_origins_env = os.getenv("CORS_ORIGINS", "").strip()
if _cors_origins_env:
    _cors_origins = [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]
_cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", "").strip() or None

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=_cors_origin_regex,
)

# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@app.post("/api/login")
async def login(body: LoginRequest):
    username = body.username
    password = body.password
    client_username = os.getenv("CLIENT_USERNAME", "")
    client_password = os.getenv("CLIENT_PASSWORD", "")
    if not client_username or not client_password:
        logger.error("CLIENT_USERNAME or CLIENT_PASSWORD not set")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication not configured",
        )
    if username != client_username or password != client_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(data={"sub": username})
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 86400,
    }

# ---------------------------------------------------------------------------
# Health (protected)
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def api_health(user: dict = Depends(get_current_user)):
    if feed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feed not initialized",
        )
    status_info = feed.get_connection_status()
    return {
        "status": "healthy",
        "redis_connected":    status_info.get("connected", False),
        "symbols_subscribed": status_info.get("symbols_subscribed", 0),
        "last_update":        status_info.get("last_update"),
        "last_redis_key":     status_info.get("last_redis_key"),
        "data_source":        status_info.get("data_source", "redis"),
        "mock_mode":          feed.mock_mode,
    }

# ---------------------------------------------------------------------------
# Stocks (protected, sort/filter)
# ---------------------------------------------------------------------------
@app.get("/api/stocks")
async def api_stocks(
    sort_by: str = "activity_vs_20d",
    order: str = "desc",
    limit: int = 500,
    search: Optional[str] = None,
    filter_type: Optional[str] = None,   # "gainers" | "losers" | None
    user: dict = Depends(get_current_user),
):
    if feed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feed not initialized",
        )

    VALID_SORT_FIELDS = {
        "iep_gap_pct", "iep_gap_inr", "iep", "prev_close",
        "volume", "buy_qty", "sell_qty", "bs_ratio",
        "change_pct", "change", "proxy_vol", "ltp",
        "preopen_activity_metric", "activity_20d_avg", "activity_vs_20d",
    }
    if sort_by not in VALID_SORT_FIELDS:
        sort_by = "activity_vs_20d"
    if order not in ("asc", "desc"):
        order = "desc"
    limit = max(1, min(500, limit))

    data   = feed.get_live_data()
    stocks = list(data.values())
    stocks, shortlist = _evaluate_stocks(stocks)
    stocks, _, is_frozen, freeze_message = _resolve_dashboard_window(stocks, shortlist)

    # Symbol search
    if search and search.strip():
        q = search.strip().upper()
        stocks = [s for s in stocks if q in (s.get("symbol") or "").upper()]

    # Gainers / Losers filter
    if filter_type == "gainers":
        stocks = [s for s in stocks if (s.get("iep_gap_pct") or 0) > 0]
    elif filter_type == "losers":
        stocks = [s for s in stocks if (s.get("iep_gap_pct") or 0) < 0]

    def sort_key(s):
        val = s.get(sort_by)
        if val is None:
            return float("-inf") if order == "desc" else float("inf")
        return val if isinstance(val, (int, float)) else 0

    stocks.sort(key=sort_key, reverse=(order == "desc"))
    stocks = stocks[:limit]

    ts = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "stocks":    stocks,
        "count":     len(stocks),
        "timestamp": ts,
        "is_frozen": is_frozen,
        "freeze_message": freeze_message,
        "refresh_interval_seconds": _dashboard_refresh_seconds,
    }


@app.get("/api/shortlist")
async def api_shortlist(
    limit: int = 100,
    user: dict = Depends(get_current_user),
):
    if feed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feed not initialized",
        )

    limit = max(1, min(500, limit))
    data = feed.get_live_data()
    stocks = list(data.values())
    _, shortlist = _evaluate_stocks(stocks)
    _, shortlist, is_frozen, freeze_message = _resolve_dashboard_window(stocks, shortlist)
    shortlist = shortlist[:limit]

    return {
        "shortlist": shortlist,
        "count": len(shortlist),
        "is_frozen": is_frozen,
        "freeze_message": freeze_message,
        "refresh_interval_seconds": _dashboard_refresh_seconds,
        "timestamp": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
    }

# ---------------------------------------------------------------------------
# WebSocket /ws/live?token=...
# ---------------------------------------------------------------------------
@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return
    try:
        verify_token(token)
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    ws_clients.add(websocket)
    logger.info("WebSocket client connected; total=%d", len(ws_clients))

    # Send immediate snapshot to newly connected client.
    try:
        if feed:
            data = feed.get_live_data()
            live_stocks = list(data.values())
            live_stocks, live_shortlist = _evaluate_stocks(live_stocks)
            stocks, shortlist, is_frozen, freeze_message = _resolve_dashboard_window(live_stocks, live_shortlist)
            status_info = feed.get_connection_status()
            gainers = sum(1 for s in stocks if (s.get("iep_gap_pct") or 0) > 0)
            losers = sum(1 for s in stocks if (s.get("iep_gap_pct") or 0) < 0)
            high_alerts = sum(1 for s in stocks if s.get("alert_level") == "HIGH")
            await websocket.send_json(
                {
                    "type": "update",
                    "data": stocks,
                    "shortlist": shortlist,
                    "timestamp": status_info.get("last_update") or datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                    "phase": "📌 PRE-OPEN SNAPSHOT FROZEN" if is_frozen else "🟡 PRE-OPEN LIVE",
                    "is_frozen": is_frozen,
                    "freeze_message": freeze_message,
                    "refresh_interval_seconds": _dashboard_refresh_seconds,
                    "stats": {
                        "total": len(stocks),
                        "gainers": gainers,
                        "losers": losers,
                        "high_alerts": high_alerts,
                        "shortlisted": len(shortlist),
                    },
                }
            )
    except Exception:
        pass

    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if msg.strip().lower() == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.debug("WebSocket recv error: %s", e)
                break
    finally:
        ws_clients.discard(websocket)
        logger.info("WebSocket client disconnected; total=%d", len(ws_clients))
        try:
            await websocket.close()
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Background broadcast task
# ---------------------------------------------------------------------------
async def broadcast_loop():
    """Push updates only when Redis publishes a new snapshot key (DB-rate reflection)."""
    from datetime import datetime, timezone

    # Phase helper
    def current_phase_label() -> str:
        now = datetime.now().strftime("%H:%M:%S")
        if "08:45:00" <= now < "09:00:00":
            return "Awaiting Pre-Open (8:58–9:00)"
        elif "09:00:00" <= now <= _preopen_freeze_at:
            return "🟡 PRE-OPEN LIVE"
        elif now > _preopen_freeze_at:
            return "📌 PRE-OPEN SNAPSHOT FROZEN"
        elif now >= "09:15:00":
            return "🟢 Regular Market Open"
        return "🔴 PRE-OPEN CLOSED"

    last_broadcast_key: str | None = None
    last_snapshot_count: int | None = None
    last_frozen_state: bool | None = None

    while True:
        try:
            await asyncio.sleep(1)
            if not feed:
                continue

            data = feed.get_live_data()
            live_stocks = list(data.values())
            live_stocks, live_shortlist = _evaluate_stocks(live_stocks)
            stocks, shortlist, is_frozen, freeze_message = _resolve_dashboard_window(live_stocks, live_shortlist)
            status_info = feed.get_connection_status()
            current_key = status_info.get("last_redis_key")
            current_snapshot_count = int(status_info.get("snapshot_count") or 0)

            key_changed = bool(current_key and current_key != last_broadcast_key)
            snapshot_changed = last_snapshot_count is None or current_snapshot_count != last_snapshot_count
            freeze_changed = (last_frozen_state is None) or (is_frozen != last_frozen_state)
            if not snapshot_changed and not freeze_changed:
                continue

            # Stats for cards
            gainers     = sum(1 for s in stocks if (s.get("iep_gap_pct") or 0) > 0)
            losers      = sum(1 for s in stocks if (s.get("iep_gap_pct") or 0) < 0)
            high_alerts = sum(1 for s in stocks if s.get("alert_level") == "HIGH")

            payload = {
                "type":        "update",
                "data":        stocks,
                "shortlist":   shortlist,
                "timestamp":   status_info.get("last_update") or datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                "phase":       current_phase_label(),
                "is_frozen":   is_frozen,
                "freeze_message": freeze_message,
                "refresh_interval_seconds": _dashboard_refresh_seconds,
                "stats": {
                    "total":       len(stocks),
                    "gainers":     gainers,
                    "losers":      losers,
                    "high_alerts": high_alerts,
                    "shortlisted": len(shortlist),
                },
            }

            dead = set()
            for ws in ws_clients:
                try:
                    await ws.send_json(payload)
                except Exception:
                    dead.add(ws)
            for ws in dead:
                ws_clients.discard(ws)
                try:
                    await ws.close()
                except Exception:
                    pass

            if current_key:
                last_broadcast_key = current_key
            last_snapshot_count = current_snapshot_count
            last_frozen_state = is_frozen

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception("Broadcast loop error: %s", e)

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    global feed, _broadcast_task, _scheduler
    logger.info("Starting up Pre-Open Scanner v2 (Redis feed)...")

    config  = get_config()
    scanner = config.get("scanner", {})
    storage = config.get("storage", {})

    # mock_mode: default False (we have real Redis)
    mock_mode = scanner.get("mock_mode", False)
    if os.getenv("MOCK_MODE", "").lower() in ("true", "1", "yes"):
        mock_mode = True
    elif os.getenv("MOCK_MODE", "").lower() in ("false", "0", "no"):
        mock_mode = False

    symbols = get_nifty500_symbols()   # plain symbols: ["RELIANCE", "TCS", ...]

    feed = RedisDataFeed(
        symbols=symbols,
        mock_mode=mock_mode,
        key_scan_interval_sec=int(scanner.get("update_interval_seconds", 1)),
        snapshot_retention_days=int(storage.get("snapshot_retention_days", 7)),
    )
    feed.connect()
    logger.info(
        "RedisDataFeed started (mock_mode=%s, symbols=%d)",
        mock_mode, len(symbols)
    )

    _broadcast_task = asyncio.create_task(broadcast_loop())
    logger.info("Broadcast task started.")

    # --- APScheduler: save daily final snapshot at 9:10 AM IST ---
    daily_save_time = str(storage.get("daily_save_time", "09:10"))
    save_hour, save_minute = (int(x) for x in daily_save_time.split(":"))
    _scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    _scheduler.add_job(
        _save_daily_final,
        trigger="cron",
        hour=save_hour,
        minute=save_minute,
        id="daily_final_save",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("APScheduler started: daily save at %s IST", daily_save_time)


@app.on_event("shutdown")
async def shutdown():
    global feed, _broadcast_task, _scheduler
    logger.info("Shutting down...")
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
    if _broadcast_task and not _broadcast_task.done():
        _broadcast_task.cancel()
        try:
            await _broadcast_task
        except asyncio.CancelledError:
            pass
    for ws in list(ws_clients):
        try:
            await ws.close()
        except Exception:
            pass
    ws_clients.clear()
    if feed:
        feed.disconnect()
        feed = None
    logger.info("Shutdown complete.")

# ---------------------------------------------------------------------------
# Daily final snapshot save (APScheduler job)
# ---------------------------------------------------------------------------
CSV_COLUMNS = [
    "symbol", "iep", "prev_close", "iep_gap_pct", "iep_gap_inr",
    "buy_qty", "sell_qty", "bs_ratio", "signal", "volume",
    "alert_level", "phase", "ltp", "proxy_vol",
    "preopen_activity_metric", "activity_20d_avg", "activity_vs_20d",
    "qualified", "qualification_reasons",
]


def _save_daily_final():
    """Save the current frozen/live data as the daily final snapshot."""
    if feed is None:
        logger.warning("Daily save skipped: feed not initialized.")
        return

    data = feed.get_live_data()
    stocks = list(data.values())
    if not stocks:
        logger.warning("Daily save skipped: no stock data available.")
        return

    stocks, shortlist = _evaluate_stocks(stocks)
    today_str = date.today().isoformat()
    payload = {
        "date": today_str,
        "saved_at": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "count": len(stocks),
        "shortlist_count": len(shortlist),
        "stocks": stocks,
        "shortlist": shortlist,
    }
    out_path = _DAILY_FINAL_DIR / f"{today_str}.json"
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True)
        logger.info("Daily final snapshot saved: %s (%d stocks)", out_path.name, len(stocks))
    except Exception as e:
        logger.exception("Failed to save daily final snapshot: %s", e)


def _stocks_to_csv(stocks: list) -> str:
    """Convert a list of stock dicts to a CSV string."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for stock in stocks:
        row = dict(stock)
        reasons = row.get("qualification_reasons")
        if isinstance(reasons, list):
            row["qualification_reasons"] = "; ".join(reasons)
        writer.writerow(row)
    return output.getvalue()


# ---------------------------------------------------------------------------
# History API (protected)
# ---------------------------------------------------------------------------
@app.get("/api/history/dates")
async def api_history_dates(user: dict = Depends(get_current_user)):
    """Return list of dates that have saved daily final snapshots."""
    dates = []
    for f in sorted(_DAILY_FINAL_DIR.glob("*.json"), reverse=True):
        dates.append(f.stem)  # "2026-04-09"
    return {"dates": dates, "count": len(dates)}


@app.get("/api/history/download")
async def api_history_download(
    date_str: str,
    user: dict = Depends(get_current_user),
):
    """Download a day's final snapshot as CSV."""
    file_path = _DAILY_FINAL_DIR / f"{date_str}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"No data found for {date_str}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read snapshot file")

    stocks = payload.get("stocks", [])
    if not stocks:
        raise HTTPException(status_code=404, detail=f"No stock data in snapshot for {date_str}")

    csv_content = _stocks_to_csv(stocks)
    filename = f"preopen_snapshot_{date_str}.csv"
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/history/save-now")
async def api_history_save_now(user: dict = Depends(get_current_user)):
    """Manually trigger saving the current snapshot (for testing)."""
    _save_daily_final()
    today_str = date.today().isoformat()
    file_path = _DAILY_FINAL_DIR / f"{today_str}.json"
    if file_path.exists():
        return {"status": "saved", "date": today_str}
    raise HTTPException(status_code=500, detail="Save failed")


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"service": "Pre-Open Scanner", "version": "2.0.0", "status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy"}