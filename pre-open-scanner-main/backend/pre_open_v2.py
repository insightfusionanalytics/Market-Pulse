import os, csv, time, threading, requests
from datetime import datetime
from dotenv import load_dotenv
from fyers_apiv3.FyersWebsocket import data_ws

# ═══════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════
load_dotenv()
APP_ID       = os.getenv("FYERS_APP_ID")
ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN")
FULL_TOKEN   = f"{APP_ID}:{ACCESS_TOKEN}"
TG_TOKEN     = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = [
    "NSE:RELIANCE-EQ",
    "NSE:MAZDOCK-EQ",
    "NSE:HINDCOPPER-EQ",
    "NSE:ETERNAL-EQ",
    "NSE:RVNL-EQ"
]

START_TIME = "08:58:00"
STOP_TIME  = "09:20:00"
DATE_STR   = datetime.now().strftime("%Y%m%d")

# ═══════════════════════════════════════════════════════
# PHASE TAGGING
# ═══════════════════════════════════════════════════════
def get_phase(hms: str) -> str:
    if   hms < "09:00:00": return "PRE_BASELINE"
    elif hms < "09:07:30": return "PHASE1_ORDER_COLLECTION"
    elif hms < "09:12:00": return "PHASE2_MATCHING"
    elif hms < "09:15:00": return "PHASE3_BUFFER"
    else:                  return "REGULAR_MARKET"

# ═══════════════════════════════════════════════════════
# TELEGRAM SNAPSHOT SCHEDULE
# ═══════════════════════════════════════════════════════
SNAPSHOTS = {
    "09:00:15": "🟢 PHASE 1 START — Order Collection",
    "09:07:30": "🔴 PHASE 1 END — Order Collection Close",
    "09:08:30": "⚡ PHASE 2 — Post Auction Match",
    "09:15:10": "🚀 REGULAR MARKET OPEN",
    "09:20:05": "🏁 FINAL SUMMARY — Auto Stop"
}
sent_snaps = set()

# ═══════════════════════════════════════════════════════
# STATE
# ═══════════════════════════════════════════════════════
latest           = {}   # symbol → latest full dict
tick_count       = {}   # symbol → int
all_keys         = set()
ltp_history      = {}   # symbol → [ltp values]
one_sec_log      = {}   # "HH:MM:SS" → {symbol → dict}
written_sec_keys = set()

# ═══════════════════════════════════════════════════════
# FILES
# ═══════════════════════════════════════════════════════
os.makedirs("outputs", exist_ok=True)
RAW_FILE   = open(f"outputs/01_raw_ticks_{DATE_STR}.csv",     "w", newline="", encoding="utf-8")
SEC_FILE   = open(f"outputs/02_per_second_{DATE_STR}.csv",    "w", newline="", encoding="utf-8")
PHASE_FILE = open(f"outputs/03_phase_summary_{DATE_STR}.csv", "w", newline="", encoding="utf-8")
raw_writer = sec_writer = phase_writer = None

# ═══════════════════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════════════════
def send_telegram(text: str):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=8
        )
        if r.status_code != 200:
            print(f"[TG Error] {r.status_code}: {r.text[:80]}")
    except Exception as e:
        print(f"[TG Exception] {e}")

def gf(d, *keys):
    """Get first non-empty value from multiple possible field names."""
    for k in keys:
        v = d.get(k)
        if v not in (None, "", 0, 0.0):
            return v
    return "–"

def build_snap_msg(label: str) -> str:
    ts = datetime.now().strftime("%H:%M:%S")
    dt = datetime.now().strftime("%d %b %Y")
    lines = [
        f"<b>{label}</b>",
        f"<i>📅 {dt}  ⏰ {ts}</i>",
        "<pre>SYM          LTP    CHG%   BUY_Q   SELL_Q   PROXY  TICKS</pre>",
        "<pre>" + "─"*52 + "</pre>"
    ]
    iep_lines = ["\n<b>📌 IEP / LTP Analysis:</b>"]
    for sym in SYMBOLS:
        s = sym.split(":")[1].replace("-EQ","")
        d = latest.get(sym, {})
        ltp  = gf(d, "ltp")
        chp  = gf(d, "chp", "change_perc")
        bq   = gf(d, "tot_buy_qty",  "totalbuyqty")
        sq   = gf(d, "tot_sell_qty", "totalsellqty")
        tks  = tick_count.get(sym, 0)
        prev = d.get("prev_close_price", "–")
        op   = d.get("open_price", "–")
        pv   = "–"
        try:   pv = f"{int(bq)+int(sq):,}"
        except: pass
        try:   bq = f"{int(bq):,}"
        except: pass
        try:   sq = f"{int(sq):,}"
        except: pass
        lines.append(
            f"<pre>{s:<12}{str(ltp):>7} {str(chp):>6}%"
            f" {str(bq):>8} {str(sq):>8} {pv:>8} {tks:>5}</pre>"
        )
        hist   = ltp_history.get(sym, [])
        moved  = "✅ MOVED" if len(set(hist)) > 1 else "🔴 FROZEN"
        iep_lines.append(f"<pre>{s:<12} prev={prev}  open={op}  → {moved}</pre>")

    lines += iep_lines
    vol_note = "\n<b>📦 Vol today (0 = pre-open, >0 = trades started):</b>"
    for sym in SYMBOLS:
        s = sym.split(":")[1].replace("-EQ","")
        d = latest.get(sym, {})
        vol = d.get("vol_traded_today", 0)
        vol_note += f"\n<pre>{s:<12} vol={vol}</pre>"
    lines.append(vol_note)
    lines.append(f"\n<i>Unique fields seen: {len(all_keys)}</i>")
    lines.append(f"<i>Total ticks: {sum(tick_count.values())}</i>")
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════
# CSV WRITERS
# ═══════════════════════════════════════════════════════
def write_raw(row: dict):
    global raw_writer
    if raw_writer is None:
        raw_writer = csv.DictWriter(RAW_FILE, fieldnames=list(row.keys()), extrasaction="ignore")
        raw_writer.writeheader()
    else:
        new = set(row.keys()) - set(raw_writer.fieldnames)
        if new:
            alert = f"🆕 NEW FIELD(S) @ {row.get('_ts','?')}: {new}"
            print(f"\n{'!'*60}\n{alert}\n{'!'*60}")
            send_telegram(f"<b>{alert}</b>")
    raw_writer.writerow(row)
    RAW_FILE.flush()

def flush_per_second():
    global sec_writer
    for sec_key in sorted(set(one_sec_log.keys()) - written_sec_keys):
        for sym, d in one_sec_log[sec_key].items():
            row = {
                "_second": sec_key,
                "_phase":  get_phase(sec_key),
                "symbol":  sym,
                "ticks":   tick_count.get(sym, 0)
            }
            row.update(d)
            if sec_writer is None:
                sec_writer = csv.DictWriter(SEC_FILE, fieldnames=list(row.keys()), extrasaction="ignore")
                sec_writer.writeheader()
            sec_writer.writerow(row)
        written_sec_keys.add(sec_key)
    SEC_FILE.flush()

def write_phase_snapshot(label: str):
    global phase_writer
    ts = datetime.now().strftime("%H:%M:%S.%f")
    for sym in SYMBOLS:
        d   = latest.get(sym, {})
        row = {
            "_ts":          ts,
            "_phase_label": label,
            "_phase":       get_phase(ts[:8]),
            "symbol":       sym,
            "tick_count":   tick_count.get(sym, 0),
            "ltp_moved":    1 if len(set(ltp_history.get(sym, []))) > 1 else 0
        }
        row.update(d)
        if phase_writer is None:
            phase_writer = csv.DictWriter(PHASE_FILE, fieldnames=list(row.keys()), extrasaction="ignore")
            phase_writer.writeheader()
        phase_writer.writerow(row)
    PHASE_FILE.flush()

def close_all():
    flush_per_second()
    write_phase_snapshot("SESSION_END")
    for f in [RAW_FILE, SEC_FILE, PHASE_FILE]:
        try: f.close()
        except: pass
    print(f"\n✅ All 3 CSVs saved to outputs/")

# ═══════════════════════════════════════════════════════
# WEBSOCKET CALLBACKS
# ═══════════════════════════════════════════════════════
def onmessage(msg):
    ts     = datetime.now().strftime("%H:%M:%S.%f")
    hms    = ts[:8]
    sym    = msg.get("symbol", msg.get("s", "UNKNOWN"))
    phase  = get_phase(hms)

    all_keys.update(msg.keys())
    if sym not in latest: latest[sym] = {}
    latest[sym].update(msg)
    tick_count[sym] = tick_count.get(sym, 0) + 1

    ltp_val = msg.get("ltp")
    if ltp_val:
        if sym not in ltp_history: ltp_history[sym] = []
        ltp_history[sym].append(ltp_val)

    # Raw CSV
    row = {"_ts": ts, "_phase": phase, "symbol": sym}
    row.update(msg)
    write_raw(row)

    # Per-second log
    if hms not in one_sec_log: one_sec_log[hms] = {}
    if sym not in one_sec_log[hms]: one_sec_log[hms][sym] = {}
    one_sec_log[hms][sym].update(msg)

    # Telegram triggers
    for snap_time, label in SNAPSHOTS.items():
        if hms >= snap_time and snap_time not in sent_snaps:
            write_phase_snapshot(label)
            send_telegram(build_snap_msg(label))
            sent_snaps.add(snap_time)
            print(f"\n{'='*60}\n📬 TELEGRAM: {label} @ {ts}\n{'='*60}")

    # One-line terminal tick
    short = sym.split(":")[1].replace("-EQ","") if ":" in sym else sym
    tp    = msg.get("type","?")
    ltp   = msg.get("ltp","–")
    bq    = msg.get("tot_buy_qty","–")
    sq    = msg.get("tot_sell_qty","–")
    print(f"[{ts}] {short:<14} ltp={str(ltp):<9} bq={str(bq):<9} sq={str(sq):<9} t={tp} phase={phase} #{tick_count[sym]}")

def onerror(msg):
    print(f"\n[❌ ERROR] {msg}")
    send_telegram(f"❌ <b>WS Error @ {datetime.now().strftime('%H:%M:%S')}</b>\n{msg}")

def onclose(msg):
    print(f"\n[CLOSED] {msg}")
    close_all()

def onopen():
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n✅ WebSocket Connected @ {ts}")
    fyers.subscribe(symbols=SYMBOLS, data_type="SymbolUpdate")
    fyers.subscribe(symbols=SYMBOLS, data_type="DepthUpdate")
    send_telegram(
        f"🔌 <b>Pre-Open Scanner V2 CONNECTED</b>\n"
        f"<i>⏰ {ts}  📅 {datetime.now().strftime('%d %b %Y')}</i>\n\n"
        f"<b>Symbols:</b> {[s.split(':')[1].replace('-EQ','') for s in SYMBOLS]}\n"
        f"<b>Window:</b> {START_TIME} → {STOP_TIME} (auto-stop)\n\n"
        f"<b>📁 Output files:</b>\n"
        f"  01_raw_ticks_{DATE_STR}.csv\n"
        f"  02_per_second_{DATE_STR}.csv\n"
        f"  03_phase_summary_{DATE_STR}.csv\n\n"
        f"<b>📬 Snapshots at:</b> 9:00:15 | 9:07:30 | 9:08:30 | 9:15:10 | 9:20:05"
    )
    fyers.keep_running()

# ═══════════════════════════════════════════════════════
# BACKGROUND LOOP — 10s table + 60s flush + auto-stop
# ═══════════════════════════════════════════════════════
def background_loop():
    counter = 0
    while True:
        time.sleep(10)
        counter += 1
        now = datetime.now().strftime("%H:%M:%S")
        phase = get_phase(now)

        # ── AUTO STOP ──────────────────────────────────
        if now >= STOP_TIME:
            print(f"\n⏹ AUTO-STOP @ {now} — saving all files...")
            close_all()
            send_telegram(
                f"⏹ <b>Auto-stopped @ {now}</b>\n\n"
                f"<b>Final tick counts:</b>\n" +
                "\n".join([f"  {s.split(':')[1].replace('-EQ','')}: {tick_count.get(s,0)} ticks" for s in SYMBOLS]) +
                f"\n\n<b>All fields captured:</b>\n<pre>{sorted(all_keys)}</pre>"
            )
            os._exit(0)

        # ── FLUSH per-second CSV every 60s ─────────────
        if counter % 6 == 0:
            flush_per_second()
            print(f"[{now}] 💾 Per-second CSV flushed ({len(written_sec_keys)} seconds logged)")

        # ── TERMINAL SUMMARY TABLE ──────────────────────
        print(f"\n[{now}] ── {phase} ── 10s SUMMARY ─────────────────────────")
        print(f"  {'SYM':<14}{'LTP':>9}{'CHG%':>8}{'BUY_QTY':>12}{'SELL_QTY':>11}{'PROXY':>10}{'TICKS':>7}")
        print("  " + "─"*68)
        for sym in SYMBOLS:
            s   = sym.split(":")[1].replace("-EQ","")
            d   = latest.get(sym, {})
            ltp = d.get("ltp","–")
            chp = d.get("chp", d.get("change_perc","–"))
            bq  = d.get("tot_buy_qty",  d.get("totalbuyqty","–"))
            sq  = d.get("tot_sell_qty", d.get("totalsellqty","–"))
            tks = tick_count.get(sym, 0)
            pv  = "–"
            try: pv = f"{int(bq)+int(sq):,}"
            except: pass
            print(f"  {s:<14}{str(ltp):>9}{str(chp):>8}%{str(bq):>12}{str(sq):>11}{pv:>10}{tks:>7}")
        print(f"  → Total ticks: {sum(tick_count.values())} | Fields: {len(all_keys)}")

# ═══════════════════════════════════════════════════════
# WAIT LOOP — holds until 8:58 AM
# ═══════════════════════════════════════════════════════
def wait_until(target_hms: str):
    while True:
        now = datetime.now().strftime("%H:%M:%S")
        if now >= target_hms:
            print(f"\n✅ {target_hms} reached — connecting now...")
            return
        try:
            t1 = datetime.strptime(now,        "%H:%M:%S")
            t2 = datetime.strptime(target_hms, "%H:%M:%S")
            secs = int((t2 - t1).total_seconds())
            print(f"  ⏳ Waiting for {target_hms}... {secs}s remaining", end="\r")
        except: pass
        time.sleep(5)

# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════
if __name__ == "__main__":
    print("="*62)
    print("   NSE PRE-OPEN LIVE CAPTURE V2")
    print(f"   Date    : {DATE_STR}")
    print(f"   Window  : {START_TIME} → {STOP_TIME} (auto-stop)")
    print(f"   Symbols : {[s.split(':')[1] for s in SYMBOLS]}")
    print(f"   Telegram: Chat {TG_CHAT_ID}")
    print("="*62)

    wait_until(START_TIME)

    fyers = data_ws.FyersDataSocket(
        access_token=FULL_TOKEN,
        on_connect=onopen,
        on_message=onmessage,
        on_error=onerror,
        on_close=onclose,
        reconnect=True
    )

    threading.Thread(target=background_loop, daemon=True).start()

    try:
        fyers.connect()
    except KeyboardInterrupt:
        print("\n⏹ Ctrl+C — saving files...")
        close_all()
