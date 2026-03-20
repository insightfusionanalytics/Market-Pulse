"""
Fyers live feed integration for Pre-Open Scanner.

Connects to Fyers WebSocket feed for real-time market data with optional mock mode.
Uses fyers-apiv3 for live data; mock mode generates realistic random ticks.
Reference: https://myapi.fyers.in/docsv3/#websocket-v3
"""

import logging
import random
import threading
import time
from datetime import datetime, timezone
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("FyersDataFeed")

# Max symbols per Fyers connection (API limit); we use one connection, subscribe in batches of 200
SYMBOLS_PER_CONNECTION = 200
MAX_RECONNECT_ATTEMPTS = 3
MOCK_UPDATE_INTERVAL_SEC = 0.5


def _standard_tick(
    symbol: str, ltp: float, change: float, change_pct: float,
    volume: int, buy_qty: int, sell_qty: int,
    high: float, low: float, open_price: float, prev_close: float,
    lower_ckt: float = 0.0, upper_ckt: float = 0.0,
    timestamp: str | None = None, phase: str = "UNKNOWN"
) -> dict[str, Any]:
    bs_ratio = round(buy_qty / sell_qty, 2) if sell_qty > 0 else 0.0
    proxy_vol = buy_qty + sell_qty
    iep_gap_pct = abs(round((open_price - prev_close) / prev_close * 100, 3)) if prev_close > 0 else 0.0
    alert_level = (
        "HIGH" if iep_gap_pct >= 2.0 or bs_ratio < 0.4 or bs_ratio > 2.5 else
        "MEDIUM" if iep_gap_pct >= 0.5 else
        "NORMAL"
    )
    return {
        "symbol": symbol,
        "ltp": round(ltp, 2),
        "iep": round(open_price, 2),
        "prev_close": round(prev_close, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "volume": volume,
        "buy_qty": buy_qty,
        "sell_qty": sell_qty,
        "bs_ratio": bs_ratio,
        "proxy_vol": proxy_vol,
        "iep_gap_pct": iep_gap_pct,
        "flagged": False,
        "tick_count": 0,
        "high": round(high, 2),
        "low": round(low, 2),
        "open": round(open_price, 2),
        "lower_ckt": round(lower_ckt, 2),
        "upper_ckt": round(upper_ckt, 2),
        "phase": phase,
        "alert_level": alert_level,
        "timestamp": timestamp or datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
    }


class FyersDataFeed:
    """
    Real-time market data feed via Fyers WebSocket or mock mode.

    - mock_mode=True: background thread generates random ticks (no Fyers connection).
    - mock_mode=False: uses fyers_apiv3 FyersWebsocket, subscribes to SymbolUpdate (full tick).
    """

    def __init__(
        self,
        app_id: str,
        access_token: str,
        symbols: list[str],
        mock_mode: bool = True,
    ):
        """
        Initialize the feed.

        Args:
            app_id: Fyers app ID (used for live mode token format "app_id:access_token").
            access_token: Fyers access token (live mode only).
            symbols: List of Fyers symbols, e.g. ["NSE:RELIANCE-EQ", ...].
            mock_mode: If True, generate random data; if False, connect to Fyers WebSocket.
        """
        self.app_id = app_id
        self.access_token = access_token
        self.symbols = list(symbols)[:600]  # Cap at 600 (3 * 200)
        self.mock_mode = mock_mode

        self._lock = threading.Lock()
        self._latest_data: dict[str, dict[str, Any]] = {}
        self._connected = False
        self._symbols_subscribed = 0
        self._last_update: str | None = None
        self._mock_stop = threading.Event()
        self._mock_thread: threading.Thread | None = None
        self._fyers_sockets: list[Any] = []
        self._fyers_ws: Any = None
        self._reconnect_count = 0

    def _on_message(self, message: dict[str, Any]) -> None:
        """
        Parse Fyers tick and store in standardized format.
        Called from Fyers callback (or mock thread).
        """
        try:
            if not isinstance(message, dict):
                return
            # Control/auth messages
            if message.get("type") in ("cn", "ful", "sub", "unsub", "lit", "cp", "cr"):
                logger.debug("Control message: %s", message)
                return
            symbol = message.get("symbol")
            if not symbol:
                return
            ltp = message.get("ltp")
            if ltp is None:
                return
            prev_close = message.get("prev_close_price", ltp)
            change = message.get("ch", ltp - prev_close)
            change_pct = message.get("chp", (change / prev_close * 100) if prev_close else 0)
            buy_qty = int(message.get("tot_buy_qty", 0))
            sell_qty = int(message.get("tot_sell_qty", 0))
            high = message.get("high_price", ltp)
            low = message.get("low_price", ltp)
            open_price = message.get("open_price", prev_close)
            ts = message.get("last_traded_time") or message.get("exch_feed_time")
            if ts is not None and not isinstance(ts, str):
                ts = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
            elif ts is None:
                ts = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")

            lower_ckt = float(message.get("lower_ckt", 0.0) or 0.0)
            upper_ckt = float(message.get("upper_ckt", 0.0) or 0.0)

            vol_today = int(message.get("vol_traded_today", 0) or 0)
            ist_time = datetime.now().strftime("%H:%M:%S")
            if ist_time < "09:00:00":
                phase = "PRE_BASELINE"
            elif ist_time >= "09:15:00":
                phase = "REGULAR_MARKET"
            elif vol_today > 0 and ist_time < "09:15:00":
                phase = "PHASE2_MATCHING"
            else:
                phase = "PHASE1_ORDER_COLLECTION"

            tick = _standard_tick(
                symbol=symbol,
                ltp=float(ltp),
                change=float(change),
                change_pct=float(change_pct),
                volume=vol_today,
                buy_qty=buy_qty,
                sell_qty=sell_qty,
                high=float(high),
                low=float(low),
                open_price=float(open_price),
                prev_close=float(prev_close),
                lower_ckt=lower_ckt,
                upper_ckt=upper_ckt,
                timestamp=ts if isinstance(ts, str) else None,
                phase=phase,
            )
            with self._lock:
                self._latest_data[symbol] = tick
                self._last_update = tick["timestamp"]
        except Exception as e:
            logger.exception("Error parsing Fyers message: %s", e)

    def _mock_loop(self) -> None:
        """Background thread: generate random ticks for all symbols every 0.5s."""
        logger.info("Mock feed started for %d symbols", len(self.symbols))
        random.seed()
        state: dict[str, tuple[float, int]] = {}
        for s in self.symbols:
            base_price = random.uniform(100, 5000)
            state[s] = (base_price, 0)

        while not self._mock_stop.is_set():
            try:
                now = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
                for symbol in self.symbols:
                    ltp_old, vol_base = state[symbol]
                    change_pct = random.uniform(-2.0, 2.0)
                    if random.random() < 0.3:
                        change_pct = random.uniform(-0.1, 0.1)
                    ltp_new = ltp_old * (1 + change_pct / 100)
                    change = ltp_new - ltp_old
                    vol_delta = random.randint(1000, 50000)
                    vol_base += vol_delta
                    buy_qty = vol_base // 2 + random.randint(-10000, 10000)
                    sell_qty = vol_base - buy_qty
                    if buy_qty < 0:
                        buy_qty, sell_qty = 0, vol_base
                    if sell_qty < 0:
                        sell_qty, buy_qty = 0, vol_base
                    high = max(ltp_old, ltp_new) * (1 + random.uniform(0, 0.005))
                    low = min(ltp_old, ltp_new) * (1 - random.uniform(0, 0.005))
                    open_price = ltp_old
                    prev_close = state[symbol][0] if symbol in state else ltp_old

                    ist_time_mock = datetime.now().strftime("%H:%M:%S")
                    if ist_time_mock < "09:00:00":
                        mock_phase = "PRE_BASELINE"
                    elif ist_time_mock >= "09:15:00":
                        mock_phase = "REGULAR_MARKET"
                    else:
                        mock_phase = "PHASE1_ORDER_COLLECTION"

                    tick = _standard_tick(
                        symbol=symbol,
                        ltp=ltp_new,
                        change=change,
                        change_pct=change_pct,
                        volume=vol_base,
                        buy_qty=buy_qty,
                        sell_qty=sell_qty,
                        high=high,
                        low=low,
                        open_price=open_price,
                        prev_close=prev_close,
                        lower_ckt=0.0,
                        upper_ckt=0.0,
                        timestamp=now,
                        phase=mock_phase,
                    )
                    with self._lock:
                        self._latest_data[symbol] = tick
                        self._last_update = now
                    state[symbol] = (ltp_new, vol_base)
            except Exception as e:
                logger.exception("Mock loop error: %s", e)
            self._mock_stop.wait(timeout=MOCK_UPDATE_INTERVAL_SEC)

        logger.info("Mock feed stopped")

    def connect(self) -> None:
        """
        Start the feed.
        - Mock: start background thread generating random data.
        - Live: initialize Fyers WebSocket and subscribe in batches of 200 (up to 3 batches).
        """
        if self.mock_mode:
            self._connected = True
            self._symbols_subscribed = len(self.symbols)
            self._mock_stop.clear()
            self._mock_thread = threading.Thread(target=self._mock_loop, daemon=True)
            self._mock_thread.start()
            logger.info("Mock mode: connected, symbols=%d", self._symbols_subscribed)
            return

        try:
            from fyers_apiv3.FyersWebsocket import data_ws

            token = f"{self.app_id}:{self.access_token}"

            def on_connect() -> None:
                try:
                    chunks = [
                        self.symbols[i : i + SYMBOLS_PER_CONNECTION]
                        for i in range(0, len(self.symbols), SYMBOLS_PER_CONNECTION)
                    ]
                    for idx, chunk in enumerate(chunks):
                        self._fyers_ws.subscribe(
                            symbols=chunk,
                            data_type="SymbolUpdate",
                            channel=11,
                        )
                        logger.info("Subscribed batch %d: %d symbols on channel 11", idx + 1, len(chunk))
                        time.sleep(0.5)
                    with self._lock:
                        self._symbols_subscribed = len(self.symbols)
                        self._connected = True
                    self._fyers_ws.keep_running()
                except Exception as e:
                    logger.exception("on_connect subscribe error: %s", e)

            def on_error(err: Any) -> None:
                logger.error("Fyers WebSocket error: %s", err)
                if self._reconnect_count >= MAX_RECONNECT_ATTEMPTS:
                    logger.error("Max reconnect attempts (%d) reached", MAX_RECONNECT_ATTEMPTS)

            def on_close(msg: Any) -> None:
                logger.warning("Fyers WebSocket closed: %s", msg)
                with self._lock:
                    self._connected = False

            self._fyers_ws = data_ws.FyersDataSocket(
                access_token=token,
                write_to_file=False,
                log_path="",
                litemode=False,
                reconnect=True,
                reconnect_retry=MAX_RECONNECT_ATTEMPTS,
                on_message=self._on_message,
                on_error=on_error,
                on_connect=on_connect,
                on_close=on_close,
            )
            self._fyers_ws.connect()
            time.sleep(2)
            with self._lock:
                self._connected = True
            logger.info("Fyers WebSocket connect() called; subscription in on_connect")
        except Exception as e:
            logger.exception("Fyers connect failed: %s", e)
            with self._lock:
                self._connected = False
            raise

    def subscribe(self, symbols: list[str]) -> None:
        """
        Subscribe to symbols. In live mode, split across channels (200 per channel, max 3 channels).
        In mock mode, just updates the symbol list for next connect (or already running mock uses existing list).
        """
        self.symbols = list(symbols)[:600]
        if self.mock_mode and self._mock_thread and self._mock_thread.is_alive():
            with self._lock:
                self._symbols_subscribed = len(self.symbols)
            logger.info("Mock mode: symbol list updated to %d", len(self.symbols))
            return
        if not self.mock_mode and self._fyers_ws and self._connected:
            chunks = [
                self.symbols[i : i + SYMBOLS_PER_CONNECTION]
                for i in range(0, len(self.symbols), SYMBOLS_PER_CONNECTION)
            ]
            for idx, chunk in enumerate(chunks):
                try:
                    self._fyers_ws.subscribe(
                        symbols=chunk,
                        data_type="SymbolUpdate",
                        channel=11,
                    )
                    logger.info("Subscribed batch %d: %d symbols", idx + 1, len(chunk))
                except Exception as e:
                    logger.exception("Subscribe error: %s", e)
            with self._lock:
                self._symbols_subscribed = len(self.symbols)

    def get_live_data(self) -> dict[str, dict[str, Any]]:
        """Return latest tick for each symbol. Thread-safe."""
        with self._lock:
            return dict(self._latest_data)

    def get_connection_status(self) -> dict[str, Any]:
        """Return connected, symbols_subscribed, last_update."""
        with self._lock:
            return {
                "connected": self._connected,
                "symbols_subscribed": self._symbols_subscribed,
                "last_update": self._last_update,
            }

    def disconnect(self) -> None:
        """Close all connections and stop mock thread."""
        if self.mock_mode:
            self._mock_stop.set()
            if self._mock_thread and self._mock_thread.is_alive():
                self._mock_thread.join(timeout=2)
            self._mock_thread = None
            with self._lock:
                self._connected = False
            logger.info("Mock feed disconnected")
            return
        if self._fyers_ws:
            try:
                self._fyers_ws.close_connection()
            except Exception as e:
                logger.exception("Error closing Fyers connection: %s", e)
            self._fyers_ws = None
        with self._lock:
            self._connected = False
        logger.info("Fyers feed disconnected")


if __name__ == "__main__":
    # Quick test: mock mode with Nifty 50 symbols
    from nifty500 import get_nifty500_symbols

    symbols = get_nifty500_symbols()
    feed = FyersDataFeed(
        app_id="",
        access_token="",
        symbols=symbols,
        mock_mode=True,
    )
    feed.connect()
    print("Mock feed running 5s...")
    time.sleep(5)
    data = feed.get_live_data()
    status = feed.get_connection_status()
    print("Status:", status)
    print("Sample tick (first symbol):", list(data.values())[0] if data else None)
    feed.disconnect()
    print("Done.")
