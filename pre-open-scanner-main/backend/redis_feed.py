"""
Redis Pre-Open Data Feed for NSE Pre-Open Scanner.

Key facts confirmed from Pradeep Ji:
- Feed is automated daily, no manual start needed
- First snapshot (~9:00:30-9:00:45) contains PREVIOUS DAY data from NSE
- Real today's data starts from 2nd snapshot (~9:01:00)
- Total ~15 snapshots: 1 stale + 14 real at 30-second intervals (9:00 to 9:08)
- Feed covers all NSE stocks; we filter to Nifty 500 EQ only
"""

import json
import logging
import os
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import redis

logger = logging.getLogger("RedisDataFeed")

DEFAULT_KEY_SCAN_INTERVAL_SEC = 1
DEFAULT_SNAPSHOT_RETENTION_DAYS = 7

REDIS_HOST     = os.getenv("REDIS_HOST", "154.61.76.83")
REDIS_PORT     = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "Myrdp@123.#")
REDIS_DB       = int(os.getenv("REDIS_DB", "3"))

BS_BUY_THRESHOLD  = 1.5
BS_SELL_THRESHOLD = 0.5
ALERT_HIGH_GAP_PCT  = 2.0
ALERT_HIGH_BS_LOW   = 0.4
ALERT_HIGH_BS_HIGH  = 2.5
ALERT_MEDIUM_GAP    = 0.5

STALE_SNAPSHOT_CUTOFF = "090000"


def _compute_signal(bs_ratio):
    if bs_ratio is None:
        return "NEUTRAL"
    if bs_ratio > BS_BUY_THRESHOLD:
        return "BUY BIAS"
    if bs_ratio < BS_SELL_THRESHOLD:
        return "SELL BIAS"
    return "NEUTRAL"


def _compute_alert_level(iep_gap_pct, bs_ratio):
    if bs_ratio is None:
        return "NORMAL"
    if iep_gap_pct >= ALERT_HIGH_GAP_PCT or bs_ratio < ALERT_HIGH_BS_LOW or bs_ratio > ALERT_HIGH_BS_HIGH:
        return "HIGH"
    if iep_gap_pct >= ALERT_MEDIUM_GAP:
        return "MEDIUM"
    return "NORMAL"


def _get_market_phase():
    now = datetime.now().strftime("%H:%M:%S")
    if now < "08:45:00":
        return "PRE_BASELINE"
    elif now < "09:00:00":
        return "AWAITING_PREOPEN"
    elif now <= "09:07:30":
        return "PHASE1_ORDER_COLLECTION"
    elif now < "09:15:00":
        return "PHASE2_MATCHING"
    else:
        return "REGULAR_MARKET"


def _parse_redis_key_time(redis_key: str) -> str:
    """preopen:YYYYMMDD:HHMM or preopen:YYYYMMDD:HHMMSS -> 'HH:MM:SS'."""
    try:
        time_part = redis_key.split(":")[-1]
        if len(time_part) >= 6:
            return f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
        if len(time_part) >= 4:
            return f"{time_part[:2]}:{time_part[2:4]}:00"
    except Exception:
        pass
    return datetime.now().strftime("%H:%M:%S")


def _is_stale_snapshot(redis_key: str) -> bool:
    """First NSE snapshot at 9:00 contains previous day data."""
    try:
        time_part = redis_key.split(":")[-1]
        normalized = time_part if len(time_part) >= 6 else f"{time_part[:4]}00"
        return normalized <= STALE_SNAPSHOT_CUTOFF
    except Exception:
        return False


def _build_stock_dict(symbol, iep, prev_close, buy_qty, sell_qty, volume,
                      change_pct, redis_key, series="EQ"):
    iep_gap_inr  = round(iep - prev_close, 2)
    iep_gap_pct  = round(change_pct, 2)
    bs_ratio     = round(buy_qty / sell_qty, 2) if sell_qty > 0 else None
    signal       = _compute_signal(bs_ratio)
    alert_level  = _compute_alert_level(abs(iep_gap_pct), bs_ratio)
    proxy_vol    = buy_qty + sell_qty
    phase        = _get_market_phase()
    last_updated = _parse_redis_key_time(redis_key)
    is_stale     = _is_stale_snapshot(redis_key)
    ts_iso       = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "symbol":       symbol,
        "iep":          round(iep, 2),
        "prev_close":   round(prev_close, 2),
        "iep_gap_inr":  iep_gap_inr,
        "iep_gap_pct":  iep_gap_pct,
        "buy_qty":      buy_qty,
        "sell_qty":     sell_qty,
        "bs_ratio":     bs_ratio if bs_ratio is not None else 0.0,
        "signal":       signal,
        "volume":       volume,
        "last_updated": last_updated,
        "change_pct":   iep_gap_pct,
        "change":       iep_gap_inr,
        "alert_level":  alert_level,
        "phase":        phase,
        "series":       series,
        "is_stale":     is_stale,
        "ltp":          round(iep, 2),
        "proxy_vol":    proxy_vol,
        "open":         round(iep, 2),
        "high":         round(iep, 2),
        "low":          round(iep, 2),
        "lower_ckt":    0.0,
        "upper_ckt":    0.0,
        "flagged":      False,
        "tick_count":   0,
        "redis_key":    redis_key,
        "timestamp":    ts_iso,
    }


def _parse_snapshot(snapshot: dict, nifty500_set: set, redis_key: str) -> dict:
    """Parse snapshot dict, filter to Nifty500 EQ, stamp with correct redis_key."""
    result = {}
    stocks = snapshot.get("data", [])
    for stock in stocks:
        try:
            meta   = stock.get("metadata", {})
            detail = stock.get("detail", {})
            pre    = detail.get("preOpenMarket", {})
            symbol = meta.get("symbol", "")
            series = meta.get("series", "")
            if symbol not in nifty500_set or series != "EQ":
                continue
            iep        = float(pre.get("IEP", 0) or 0)
            prev_close = float(pre.get("prevClose", 0) or meta.get("previousClose", 0) or 0)
            buy_qty    = int(pre.get("totalBuyQuantity", 0) or 0)
            sell_qty   = int(pre.get("totalSellQuantity", 0) or 0)
            volume     = int(pre.get("totalTradedVolume", 0) or 0)
            change_pct = float(pre.get("perChange", 0) or meta.get("pChange", 0) or 0)
            if iep == 0:
                continue
            result[symbol] = _build_stock_dict(
                symbol=symbol, iep=iep, prev_close=prev_close,
                buy_qty=buy_qty, sell_qty=sell_qty, volume=volume,
                change_pct=change_pct, redis_key=redis_key, series=series,
            )
        except Exception as e:
            logger.debug("Parse error for %s: %s", stock.get("metadata", {}).get("symbol", "?"), e)
    return result


class RedisDataFeed:
    def __init__(
        self,
        symbols,
        mock_mode=False,
        app_id="",
        access_token="",
        key_scan_interval_sec: int = DEFAULT_KEY_SCAN_INTERVAL_SEC,
        snapshot_retention_days: int = DEFAULT_SNAPSHOT_RETENTION_DAYS,
    ):
        self.symbols      = symbols
        self.mock_mode    = mock_mode
        self.app_id       = app_id
        self.access_token = access_token
        self._nifty500_set       = set(symbols)
        self._lock               = threading.Lock()
        self._latest_data        = {}
        self._connected          = False
        self._symbols_subscribed = 0
        self._last_update        = None
        self._last_redis_key     = None
        self._snapshot_count     = 0
        self._stop_event         = threading.Event()
        self._thread             = None
        self._redis              = None
        self._snapshot_dir       = Path(__file__).resolve().parent / "data" / "snapshots"
        env_scan = os.getenv("REDIS_KEY_SCAN_INTERVAL_SEC")
        env_retention = os.getenv("SNAPSHOT_RETENTION_DAYS")
        self._key_scan_interval_sec = max(
            1,
            int(env_scan) if env_scan and env_scan.isdigit() else int(key_scan_interval_sec),
        )
        self._snapshot_retention_days = max(
            1,
            int(env_retention) if env_retention and env_retention.isdigit() else int(snapshot_retention_days),
        )

    def connect(self):
        self._stop_event.clear()
        target = self._mock_loop if self.mock_mode else self._live_loop
        logger.info("RedisDataFeed: %s mode", "MOCK" if self.mock_mode else "LIVE")
        self._thread = threading.Thread(target=target, daemon=True, name="RedisDataFeed")
        self._thread.start()

    def disconnect(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None
        if self._redis:
            try:
                self._redis.close()
            except Exception:
                pass
            self._redis = None
        with self._lock:
            self._connected = False

    def get_live_data(self):
        with self._lock:
            return dict(self._latest_data)

    def get_connection_status(self):
        with self._lock:
            return {
                "connected":          self._connected,
                "symbols_subscribed": self._symbols_subscribed,
                "last_update":        self._last_update,
                "last_redis_key":     self._last_redis_key,
                "snapshot_count":     self._snapshot_count,
                "data_source":        "redis" if not self.mock_mode else "mock",
            }

    def _connect_redis(self):
        try:
            self._redis = redis.Redis(
                host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
                db=REDIS_DB, decode_responses=True,
                socket_connect_timeout=10, socket_timeout=10,
            )
            self._redis.ping()
            logger.info("Redis connected (%s:%d db=%d)", REDIS_HOST, REDIS_PORT, REDIS_DB)
            with self._lock:
                self._connected = True
            return True
        except Exception as e:
            logger.error("Redis connect failed: %s", e)
            with self._lock:
                self._connected = False
            return False

    def _get_latest_key(self):
        today = date.today().strftime("%Y%m%d")
        keys  = sorted(self._redis.scan_iter(f"preopen:{today}:*"))
        return keys[-1] if keys else None

    def _persist_parsed_snapshot(self, redis_key: str, parsed: dict[str, dict], ts_iso: str) -> None:
        try:
            parts = redis_key.split(":")
            if len(parts) < 3:
                return
            day = parts[1]
            time_token = parts[2]
            payload = {
                "redis_key": redis_key,
                "timestamp": ts_iso,
                "count": len(parsed),
                "stocks": parsed,
            }
            day_dir = self._snapshot_dir / day
            day_dir.mkdir(parents=True, exist_ok=True)
            with open(day_dir / f"{time_token}.json", "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=True)
        except Exception as e:
            logger.debug("Snapshot persist failed for %s: %s", redis_key, e)

    def _prune_snapshot_history(self) -> None:
        try:
            if not self._snapshot_dir.exists():
                return
            today = datetime.now().date()
            for child in self._snapshot_dir.iterdir():
                if not child.is_dir():
                    continue
                try:
                    day = datetime.strptime(child.name, "%Y%m%d").date()
                except ValueError:
                    continue
                age_days = (today - day).days
                if age_days > self._snapshot_retention_days:
                    for f in child.glob("*.json"):
                        f.unlink(missing_ok=True)
                    child.rmdir()
        except Exception as e:
            logger.debug("Snapshot prune failed: %s", e)

    def _live_loop(self):
        retry_delay = 5
        while not self._stop_event.is_set():
            if self._connect_redis():
                break
            self._stop_event.wait(timeout=retry_delay)
            retry_delay = min(retry_delay * 2, 60)
        if self._stop_event.is_set():
            return

        logger.info("Live key scan loop started (every %ds)", self._key_scan_interval_sec)
        self._prune_snapshot_history()
        while not self._stop_event.is_set():
            loop_start = time.time()
            try:
                latest_key = self._get_latest_key()
                if latest_key is None:
                    logger.debug("No Redis key for today yet.")
                elif latest_key != self._last_redis_key:
                    raw = self._redis.get(latest_key)
                    if raw:
                        snapshot = json.loads(raw)
                        parsed   = _parse_snapshot(snapshot, self._nifty500_set, latest_key)
                        ts       = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
                        is_stale = _is_stale_snapshot(latest_key)
                        with self._lock:
                            self._latest_data        = parsed
                            self._last_redis_key     = latest_key
                            self._last_update        = ts
                            self._symbols_subscribed = len(parsed)
                            self._snapshot_count    += 1
                        self._persist_parsed_snapshot(latest_key, parsed, ts)
                        logger.info(
                            "Snapshot #%d: %s | %d stocks | stale=%s",
                            self._snapshot_count, latest_key, len(parsed), is_stale
                        )
                        self._prune_snapshot_history()
                try:
                    self._redis.ping()
                except Exception:
                    logger.warning("Redis ping failed, reconnecting...")
                    with self._lock:
                        self._connected = False
                    self._connect_redis()
            except Exception as e:
                logger.exception("Live loop error: %s", e)
                with self._lock:
                    self._connected = False
                time.sleep(5)
                self._connect_redis()

            elapsed = time.time() - loop_start
            self._stop_event.wait(timeout=max(0, self._key_scan_interval_sec - elapsed))

    def _mock_loop(self):
        import random
        random.seed(42)
        state = {}
        for sym in self.symbols:
            base = random.uniform(100, 5000)
            state[sym] = {
                "iep": base, "prev_close": base * random.uniform(0.97, 1.03),
                "buy_qty": random.randint(100000, 500000),
                "sell_qty": random.randint(100000, 500000),
                "volume": random.randint(50000, 300000),
            }
        tick_num = 0
        with self._lock:
            self._connected = True
            self._symbols_subscribed = len(self.symbols)
        while not self._stop_event.is_set():
            tick_num += 1
            mock_key = f"preopen:MOCK:{str(tick_num).zfill(4)}"
            ts = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
            new_data = {}
            for sym in self.symbols:
                s = state[sym]
                cp = random.uniform(-3.0, 3.0)
                s["iep"] = round(s["iep"] * (1 + cp / 100), 2)
                s["buy_qty"] += random.randint(1000, 50000)
                s["sell_qty"] += random.randint(1000, 50000)
                s["volume"] += random.randint(5000, 30000)
                gp = round((s["iep"] - s["prev_close"]) / s["prev_close"] * 100, 2) if s["prev_close"] else 0.0
                new_data[sym] = _build_stock_dict(
                    sym, s["iep"], s["prev_close"], s["buy_qty"], s["sell_qty"],
                    s["volume"], gp, mock_key, "EQ"
                )
            with self._lock:
                self._latest_data = new_data
                self._last_redis_key = mock_key
                self._last_update = ts
                self._symbols_subscribed = len(new_data)
                self._snapshot_count = tick_num
            self._stop_event.wait(timeout=60)