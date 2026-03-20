"""
NSE PRE-OPEN LIVE CAPTURE — OPTIMIZED v3
Merged best of both scripts.

- Every tick logged to terminal (all raw fields)
- 10-second summary table in terminal
- Saves to CSV: outputs/preopen_tick_raw.csv + outputs/preopen_1sec.csv
- Telegram snapshots at key phase times
- IEP change detection flag
- DepthUpdate + SymbolUpdate both subscribed
- New field detection alert on Telegram
- LTP movement history tracking

Run from /backend:
    python test_preopen_v3.py
"""

import csv
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from fyers_apiv3.FyersWebsocket import data_ws

load_dotenv()

# ═══════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════
APP_ID        = os.getenv("FYERS_APP_ID", "")
ACCESS_TOKEN  = os.getenv("FYERS_ACCESS_TOKEN", "")
TG_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID", "")

# Fyers expects "APPID:ACCESS_TOKEN" format for WebSocket
FULL_TOKEN = f"{APP_ID}:{ACCESS_TOKEN}"

SYMBOLS = [
    "NSE:RELIANCE-EQ",
    "NSE:MAZDOCK-EQ",
    "NSE:HINDCOPPER-EQ",
    "NSE:ETERNAL-EQ",
    "NSE:RVNL-EQ",
]

# Telegram snapshot triggers — HH:MM:SS
SNAPSHOTS = {
    "09:00:15": "🟢 PHASE 1 START — Order Entry Begins",
    "09:04:00": "📊 PHASE 1 MID — 4 Min Mark",
    "09:07:30": "🔴 PHASE 1 END — Order Window Closing",
    "09:08:30": "⚡ PHASE 2 — Auction Matching",
    "09:12:00": "🔄 PHASE 3 — Buffer / Transition",
    "09:14:45": "🚀 T-15s — Just Before Open",
    "09:15:30": "🏁 FINAL — Pre-Open Complete",
}
sent_snaps: set = set()

# ═══════════════════════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("PreOpen")

# ═══════════════════════════════════════════════════════════════
#  STATE
# ═══════════════════════════════════════════════════════════════
latest      : dict = {}   # symbol → latest merged tick dict
tick_count  : dict = {}   # symbol → int
all_keys    : set  = set()  # every field name ever seen from Fyers
one_sec_log : dict = {}   # "HH:MM:SS" → {symbol → dict}
ltp_history : dict = {}   # symbol → list of (ts, ltp)
lock = threading.Lock()

os.makedirs("outputs", exist_ok=True)
RAW_FILE = open("outputs/preopen_tick_raw.csv", "w", newline="", buffering=1)
SEC_FILE = open("outputs/preopen_1sec.csv",     "w", newline="", buffering=1)
raw_writer = None
sec_writer = None
known_raw_fields: list = []

# ═══════════════════════════════════════════════════════════════
#  CORRECT FYERS FIELD NAMES (verified from fyers-apiv3 docs)
# ═══════════════════════════════════════════════════════════════
# SymbolUpdate fields:
#   symbol, ltp, open_price, high_price, low_price, prev_close_price,
#   ch (change abs), chp (change %), vol_traded_today,
#   tot_buy_qty, tot_sell_qty, exch_feed_time, last_traded_time,
#   avg_trade_price, lower_ckt, upper_ckt
#
# DepthUpdate adds:
#   bids → list of {price, volume, ord} x5
#   asks → list of {price, volume, ord} x5

def get_field(d: dict, *keys, default="–"):
    """Try multiple key names, return first match."""
    for k in keys:
        v = d.get(k)
        if v is not None:
            return v
    return default

# ═══════════════════════════════════════════════════════════════
#  TELEGRAM
# ═══════════════════════════════════════════════════════════════
def send_telegram(text: str) -> None:
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        r = requests.post(url, data={
            "chat_id": TG_CHAT_ID,
            "text": text[:4000],  # Telegram limit
            "parse_mode": "HTML"
        }, timeout=6)
        if r.status_code != 200:
            logger.warning("Telegram failed: %s", r.text)
    except Exception as e:
        logger.error("Telegram error: %s", e)


def build_snapshot(label: str) -> str:
    ts = datetime.now().strftime("%H:%M:%S")
    with lock:
        data = dict(latest)
        keys_seen = sorted(all_keys)
        history   = dict(ltp_history)
        counts    = dict(tick_count)

    lines = [
        f"<b>{label}</b>",
        f"<i>Time: {ts} IST</i>",
        "<code>" + "─" * 52 + "</code>",
        f"<code>{'SYM':<13}{'LTP':>8}{'OPEN':>8}{'CHG%':>7}{'BUY_Q':>9}{'SELL_Q':>9}{'TICKS':>6}</code>",
        "<code>" + "─" * 52 + "</code>",
    ]

    for sym in SYMBOLS:
        short = sym.split(":")[1].replace("-EQ", "")
        d     = data.get(sym, {})

        ltp        = get_field(d, "ltp")
        open_price = get_field(d, "open_price")
        prev_close = get_field(d, "prev_close_price", "close_price")
        chp        = get_field(d, "chp", "change_perc")
        buy_qty    = get_field(d, "tot_buy_qty", "totalbuyqty")
        sell_qty   = get_field(d, "tot_sell_qty", "totalsellqty")
        tks        = counts.get(sym, 0)

        lines.append(
            f"<code>{short:<13}{str(ltp):>8}{str(open_price):>8}"
            f"{str(chp):>7}{str(buy_qty):>9}{str(sell_qty):>9}{str(tks):>6}</code>"
        )

    # IEP check block
    lines.append("\n<b>📌 IEP / open_price vs Prev Close:</b>")
    for sym in SYMBOLS:
        short = sym.split(":")[1].replace("-EQ", "")
        d     = data.get(sym, {})
        ltp        = get_field(d, "ltp")
        open_price = get_field(d, "open_price")
        prev_close = get_field(d, "prev_close_price", "close_price")

        # Did LTP ever change?
        hist = history.get(sym, [])
        ltp_values = set(v for _, v in hist)
        ltp_moved  = "✅ LTP CHANGED"  if len(ltp_values) > 1 else "🔴 LTP FROZEN"

        # Did open_price diverge from prev_close?
        try:
            iep_flag = "✅ IEP MOVING" if float(open_price) != float(prev_close) else "🔴 IEP = prev_close"
        except Exception:
            iep_flag = "?"

        lines.append(
            f"<code>{short:<12} open={open_price} prev={prev_close}"
            f"\n             {iep_flag} | {ltp_moved}</code>"
        )

    # Proxy volume
    lines.append("\n<b>📦 Order Book Proxy (buy_qty + sell_qty):</b>")
    for sym in SYMBOLS:
        short = sym.split(":")[1].replace("-EQ", "")
        d     = data.get(sym, {})
        bq    = get_field(d, "tot_buy_qty", "totalbuyqty")
        sq    = get_field(d, "tot_sell_qty", "totalsellqty")
        try:
            proxy = int(bq) + int(sq)
            ratio = round(int(bq) / int(sq), 2) if int(sq) > 0 else "∞"
        except Exception:
            proxy, ratio = "–", "–"
        lines.append(f"<code>{short:<12} proxy={proxy}  ratio={ratio}</code>")

    # All fields seen
    lines.append(f"\n<b>🔑 Fields seen so far ({len(keys_seen)}):</b>")
    lines.append(f"<code>{', '.join(keys_seen)}</code>")

    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════
#  CSV WRITING
# ═══════════════════════════════════════════════════════════════
def write_raw_csv(row: dict) -> None:
    global raw_writer, known_raw_fields
    if raw_writer is None:
        known_raw_fields = list(row.keys())
        raw_writer = csv.DictWriter(RAW_FILE, fieldnames=known_raw_fields, extrasaction="ignore")
        raw_writer.writeheader()

    # Detect new fields — alert but don't crash
    new_fields = set(row.keys()) - set(known_raw_fields)
    if new_fields:
        alert = f"🆕 NEW FIELD(S) @ {row.get('_ts', '?')}: {new_fields}"
        logger.warning(alert)
        send_telegram(f"<b>{alert}</b>")

    raw_writer.writerow(row)
    RAW_FILE.flush()

# ═══════════════════════════════════════════════════════════════
#  WEBSOCKET CALLBACKS
# ═══════════════════════════════════════════════════════════════
def onmessage(msg: dict) -> None:
    ts  = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # ms precision
    sym = msg.get("symbol", msg.get("s", ""))

    # Skip non-data control messages
    if msg.get("type") in ("cn", "ful", "sub", "unsub", "lit", "cp", "cr"):
        logger.info("CTRL | type=%s | %s", msg.get("type"), msg)
        return
    if not sym:
        logger.debug("NO SYMBOL in msg: %s", msg)
        return

    short = sym.split(":")[1].replace("-EQ", "") if ":" in sym else sym

    with lock:
        # Track all keys
        all_keys.update(msg.keys())

        # Merge into latest
        if sym not in latest:
            latest[sym] = {}
        latest[sym].update(msg)

        # Tick count
        tick_count[sym] = tick_count.get(sym, 0) + 1
        tks = tick_count[sym]

        # LTP history
        ltp_val = msg.get("ltp")
        if ltp_val is not None:
            if sym not in ltp_history:
                ltp_history[sym] = []
            ltp_history[sym].append((ts, ltp_val))

        # 1-second log
        sec_key = ts[:8]  # HH:MM:SS
        if sec_key not in one_sec_log:
            one_sec_log[sec_key] = {}
        one_sec_log[sec_key].setdefault(sym, {}).update(msg)

    # ── IEP detection ─────────────────────────────────
    ltp        = msg.get("ltp", "–")
    open_price = msg.get("open_price", "–")
    prev_close = msg.get("prev_close_price", "–")
    chp        = msg.get("chp", "–")
    buy_qty    = msg.get("tot_buy_qty", "–")
    sell_qty   = msg.get("tot_sell_qty", "–")
    volume     = msg.get("vol_traded_today", "–")

    try:
        iep_flag = "⚡ IEP≠prev" if float(open_price) != float(prev_close) else ""
    except Exception:
        iep_flag = ""

    # ── Terminal: print every raw field ───────────────
    print(f"\n[{ts}] ── {short} (tick #{tks}) {'─'*30}")
    for k, v in sorted(msg.items()):
        highlight = " ◄◄◄" if k in ("open_price", "tot_buy_qty", "tot_sell_qty", "chp") else ""
        print(f"   {k:<30} = {v}{highlight}")
    if iep_flag:
        print(f"   {'>>> ' + iep_flag:<30}")

    # ── Compact summary line ───────────────────────────
    logger.info(
        "%-12s | ltp=%-8s | open=%-8s | prev=%-8s | chp=%-6s%% | buyQ=%-10s | sellQ=%-10s | vol=%-8s %s",
        short, ltp, open_price, prev_close, chp, buy_qty, sell_qty, volume, iep_flag
    )

    # ── CSV raw ───────────────────────────────────────
    row = {"_ts": ts, "symbol": sym}
    row.update(msg)
    write_raw_csv(row)

    # ── Telegram snapshot triggers ─────────────────────
    now_str = datetime.now().strftime("%H:%M:%S")
    for snap_time, label in SNAPSHOTS.items():
        if now_str >= snap_time and snap_time not in sent_snaps:
            threading.Thread(
                target=lambda l=label, s=snap_time: _send_snap(l, s),
                daemon=True
            ).start()


def _send_snap(label: str, snap_time: str) -> None:
    sent_snaps.add(snap_time)
    msg = build_snapshot(label)
    send_telegram(msg)
    logger.info("📬 Telegram snapshot sent: %s", label)


def onerror(msg) -> None:
    logger.error("❌ WS ERROR: %s", msg)
    send_telegram(f"❌ <b>WebSocket Error:</b> {msg}")


def onclose(msg) -> None:
    logger.warning("🔴 WS CLOSED: %s", msg)
    _save_sec_csv()
    _print_final_summary()


def onopen() -> None:
    logger.info("✅ WebSocket CONNECTED")
    logger.info("📡 Subscribing: SymbolUpdate + DepthUpdate for %d symbols", len(SYMBOLS))

    fyers.subscribe(symbols=SYMBOLS, data_type="SymbolUpdate")
    fyers.subscribe(symbols=SYMBOLS, data_type="DepthUpdate")

    send_telegram(
        f"🔌 <b>Pre-Open Capture LIVE</b>\n"
        f"Symbols: {[s.split(':')[1].replace('-EQ','') for s in SYMBOLS]}\n"
        f"Snapshots at: {list(SNAPSHOTS.keys())}\n"
        f"Saving to: outputs/preopen_tick_raw.csv"
    )
    fyers.keep_running()

# ═══════════════════════════════════════════════════════════════
#  SAVE 1-SEC CSV
# ═══════════════════════════════════════════════════════════════
def _save_sec_csv() -> None:
    global sec_writer
    with lock:
        log = dict(one_sec_log)
    for sec_key in sorted(log.keys()):
        for sym, d in log[sec_key].items():
            row = {"_second": sec_key, "symbol": sym}
            row.update(d)
            if sec_writer is None:
                sec_writer = csv.DictWriter(SEC_FILE, fieldnames=list(row.keys()), extrasaction="ignore")
                sec_writer.writeheader()
            sec_writer.writerow(row)
    SEC_FILE.flush()
    SEC_FILE.close()
    RAW_FILE.close()
    logger.info("✅ Saved: outputs/preopen_tick_raw.csv")
    logger.info("✅ Saved: outputs/preopen_1sec.csv")


def _print_final_summary() -> None:
    with lock:
        counts = dict(tick_count)
        keys   = sorted(all_keys)
    print(f"\n{'='*60}")
    print("FINAL TICK COUNT PER SYMBOL:")
    for sym, cnt in counts.items():
        short = sym.split(":")[1].replace("-EQ", "") if ":" in sym else sym
        print(f"  {short:<20} {cnt} ticks")
    print(f"\nALL FIELDS SEEN FROM FYERS ({len(keys)}):")
    print(f"  {keys}")
    print(f"{'='*60}")

# ═══════════════════════════════════════════════════════════════
#  10-SECOND TERMINAL SUMMARY TABLE
# ═══════════════════════════════════════════════════════════════
def summary_loop() -> None:
    while True:
        time.sleep(10)
        now = datetime.now().strftime("%H:%M:%S")
        with lock:
            data   = dict(latest)
            counts = dict(tick_count)
            keys   = sorted(all_keys)

        print(f"\n[{now}] ━━━━━━ 10s SUMMARY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"  {'SYM':<14}{'LTP':>8}{'OPEN':>8}{'PREV':>8}{'CHG%':>7}{'BUY_Q':>10}{'SELL_Q':>10}{'PROXY':>10}{'TICKS':>7}")
        print("  " + "─" * 82)
        for sym in SYMBOLS:
            short      = sym.split(":")[1].replace("-EQ", "")
            d          = data.get(sym, {})
            ltp        = get_field(d, "ltp")
            open_price = get_field(d, "open_price")
            prev_close = get_field(d, "prev_close_price")
            chp        = get_field(d, "chp")
            buy_qty    = get_field(d, "tot_buy_qty")
            sell_qty   = get_field(d, "tot_sell_qty")
            tks        = counts.get(sym, 0)
            try:
                proxy = int(buy_qty) + int(sell_qty)
            except Exception:
                proxy = "–"
            try:
                iep_flag = "⚡" if float(open_price) != float(prev_close) else "  "
            except Exception:
                iep_flag = "  "
            print(f"  {iep_flag}{short:<12}{str(ltp):>8}{str(open_price):>8}{str(prev_close):>8}"
                  f"{str(chp):>7}{str(buy_qty):>10}{str(sell_qty):>10}{str(proxy):>10}{str(tks):>7}")
        print(f"  Fields seen: {len(keys)} → {keys}")

# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  NSE PRE-OPEN LIVE CAPTURE v3")
    print(f"  App ID   : {APP_ID}")
    print(f"  Token    : {ACCESS_TOKEN[:20]}...")
    print(f"  Symbols  : {[s.split(':')[1] for s in SYMBOLS]}")
    print(f"  Output   : outputs/preopen_tick_raw.csv")
    print(f"             outputs/preopen_1sec.csv")
    print("=" * 60)

    if not APP_ID or not ACCESS_TOKEN:
        raise ValueError("Missing FYERS_APP_ID or FYERS_ACCESS_TOKEN in .env")

    send_telegram(
        f"⏳ <b>Pre-Open Capture Initializing...</b>\n"
        f"Token: {ACCESS_TOKEN[:15]}...\n"
        f"Connecting to Fyers WebSocket..."
    )

    threading.Thread(target=summary_loop, daemon=True).start()

    fyers = data_ws.FyersDataSocket(
        access_token=FULL_TOKEN,
        write_to_file=False,
        log_path="",
        litemode=False,
        reconnect=True,
        reconnect_retry=3,
        on_connect=onopen,
        on_message=onmessage,
        on_error=onerror,
        on_close=onclose,
    )

    logger.info("🔌 Connecting...")
    fyers.connect()