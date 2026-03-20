"""
Dynamic Nifty 500 Symbol Fetcher with Comprehensive Fallback
Last Updated: Mar 2026
Next Update Due: End of March 2026

Returns plain NSE symbols: ["RELIANCE", "TCS", ...]
(No longer returns Fyers format "NSE:RELIANCE-EQ")
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import List

CACHE_FILE = "nifty500_cache.json"
CACHE_VALIDITY_DAYS = 1

NSE_NIFTY500_URL = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500"

HARDCODED_LIST_VERSION = "2026-H1"
LAST_HARDCODED_UPDATE  = "2026-03-05"
NEXT_UPDATE_DUE        = "2026-03-28"

FALLBACK_SYMBOLS = [
    # ── NIFTY 50 ──────────────────────────────────────────────────────────────
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN",
    "BHARTIARTL", "BAJFINANCE", "ASIANPAINT", "MARUTI", "HCLTECH", "KOTAKBANK", "LT",
    "AXISBANK", "TITAN", "ULTRACEMCO", "SUNPHARMA", "WIPRO", "NESTLEIND", "TATASTEEL",
    "BAJAJFINSV", "POWERGRID", "NTPC", "ONGC", "M&M", "TECHM", "ADANIPORTS", "COALINDIA",
    "DIVISLAB", "DRREDDY", "GRASIM", "HINDALCO", "INDUSINDBK", "JSWSTEEL", "BRITANNIA",
    "CIPLA", "EICHERMOT", "SHREECEM", "BAJAJ-AUTO", "TATACONSUM", "ADANIENT", "APOLLOHOSP",
    "BPCL", "UPL", "HDFCLIFE", "SBILIFE", "HEROMOTOCO", "TATAMOTORS",
    # ── NIFTY NEXT 50 ─────────────────────────────────────────────────────────
    "ADANIGREEN", "ADANIPOWER", "BANDHANBNK", "BERGEPAINT", "BOSCHLTD", "COLPAL",
    "DLF", "DMART", "GODREJCP", "HAVELLS", "HDFCAMC", "INDIGO", "IRCTC", "JINDALSTEL",
    "JUBLFOOD", "LTI", "MARICO", "MCDOWELL-N", "MOTHERSON", "NAUKRI", "NMDC", "PAGEIND",
    "PETRONET", "PIIND", "PNB", "PGHH", "SBICARD", "SIEMENS", "SRF", "TATAPOWER",
    "TRENT", "TORNTPHARM", "VEDL", "ZOMATO", "ICICIGI", "BAJAJHLDNG", "PIDILITIND",
    "ABCAPITAL", "ATGL", "GLAND", "ICICIPRULI", "VOLTAS", "MUTHOOTFIN", "TVSMOTOR",
    "CANBK", "LTTS", "IDEA", "SAIL", "INDHOTEL", "PEL",
    # ── NIFTY MIDCAP 100 ──────────────────────────────────────────────────────
    "ABFRL", "ACC", "AFFLE", "AIAENG", "AJANTPHARM", "ALKEM", "AMBUJACEM", "APOLLOTYRE",
    "ASHOKLEY", "ASTRAL", "AUROPHARMA", "BALKRISIND", "BATAINDIA", "BEL", "BHEL",
    "BIOCON", "BLUEDART", "CADILAHC", "CENTRALBK", "CHOLAFIN", "COFORGE", "CONCOR",
    "COROMANDEL", "CUMMINSIND", "CYIENT", "DABUR", "DEEPAKNTR", "DELTACORP", "DIXON",
    "ESCORTS", "EXIDEIND", "FEDERALBNK", "FORTIS", "GAIL", "GLENMARK", "GMRINFRA",
    "GNFC", "GODREJPROP", "GRINDWELL", "GSPL", "HINDZINC", "HONAUT", "IDFCFIRSTB",
    "IGL", "INDIANB", "INDIAMART", "IOC", "IRFC", "J&KBANK", "JKCEMENT", "JSWENERGY",
    "KANSAINER", "KEI", "L&TFH", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", "LUPIN",
    "M&MFIN", "MANAPPURAM", "MAZDOCK", "MFSL", "MGL", "MINDTREE", "MPHASIS", "MRF",
    "NATIONALUM", "NAM-INDIA", "NBCC", "NCC", "NHPC", "NLCINDIA", "OBEROIRLTY",
    "OFSS", "OIL", "PERSISTENT", "PFC", "PHOENIXLTD", "POLYCAB",
    "PVRINOX", "RAIN", "RAJESHEXPO", "RBLBANK", "RECLTD", "SHRIRAMFIN",
    "SRTRANSFIN", "SUNDARMFIN", "SUNTV", "SUPREMEIND", "TATACOMM",
    "TATAELXSI", "TATAINVEST", "THERMAX", "TORNTPOWER", "TRIDENT",
    "UBL", "UNIONBANK", "WHIRLPOOL", "YESBANK", "ZEEL",
    # ── ADDITIONAL ────────────────────────────────────────────────────────────
    "AARTIIND", "AKZOINDIA", "APARINDS", "ASAHIINDIA", "ATUL", "AVANTIFEED",
    "BAJAJCON", "BALRAMCHIN", "BASF", "BRIGADE", "CANFINHOME",
    "CAPLIPOINT", "CARBORUNIV", "CASTROLIND", "CEATLTD", "CENTURYPLY",
    "CENTURYTEX", "CERA", "CHAMBLFERT", "CHOLAHLDNG", "CROMPTON", "CUB",
    "DBL", "DEEPAKFERT", "DHANI", "DHUNINV", "EASTMAN", "EDELWEISS",
    "ENDURANCE", "ENGINERSIN", "EPL", "EQUITAS", "FDC",
    "FINPIPE", "FINEORG", "GAEL", "GILLETTE",
    "GICRE", "GLAXO", "GMMPFAUDLR", "GODFRYPHLP",
    "GODREJAGRO", "GODREJIND", "GRANULES", "GRAPHITE", "GREENPANEL",
    "GSHIP", "GSFC", "GUJALKALI", "GUJGASLTD", "GULFOILLUB", "HAL",
    "HATHWAY", "HATSUN", "HEIDELBERG", "HFCL",
    # ── Client specific stocks (always include) ───────────────────────────────
    "MAZDOCK", "HINDCOPPER", "ETERNAL", "RVNL",
]


def fetch_from_nse() -> List[str] | None:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        response = session.get(NSE_NIFTY500_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            data    = response.json()
            stocks  = data.get('data', [])
            symbols = [s.get('symbol') for s in stocks if s.get('symbol') and s.get('symbol') != 'NIFTY 500']
            if symbols:
                print(f"✅ Fetched {len(symbols)} stocks from NSE")
                return symbols
    except Exception as e:
        print(f"❌ NSE fetch error: {e}")
    return None


def fetch_from_zerodha() -> List[str] | None:
    try:
        response = requests.get("https://api.kite.trade/instruments", timeout=10)
        if response.status_code == 200:
            lines   = response.text.strip().split('\n')
            symbols = []
            for line in lines[1:]:
                parts = line.split(',')
                if len(parts) >= 4 and 'NSE' in line:
                    sym = parts[2] if len(parts) > 2 else ""
                    if sym and not any(x in sym for x in ['-FUT', '-CE', '-PE', 'NIFTY', 'BANKNIFTY']):
                        symbols.append(sym)
            symbols = list(set(symbols))[:500]
            if symbols:
                print(f"✅ Fetched {len(symbols)} stocks from Zerodha")
                return symbols
    except Exception as e:
        print(f"❌ Zerodha fetch error: {e}")
    return None


def load_cache() -> dict | None:
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
        cached_date = datetime.fromisoformat(cache['date'])
        if datetime.now() - cached_date < timedelta(days=CACHE_VALIDITY_DAYS):
            print(f"✅ Using cached symbols (from {cache['date'][:10]})")
            return cache
        print(f"⏰ Cache expired")
        return None
    except Exception:
        return None


def save_cache(symbols: List[str], source: str):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({
                'date':    datetime.now().isoformat(),
                'source':  source,
                'symbols': symbols,
                'count':   len(symbols),
            }, f, indent=2)
    except Exception:
        pass


def get_nifty500_symbols() -> List[str]:
    """
    Get Nifty 500 symbols as plain NSE tickers.

    Returns: ["RELIANCE", "TCS", "HDFCBANK", ...]

    Priority:
    1. Cache (if < 1 day old)
    2. NSE official API
    3. Zerodha instruments
    4. Hardcoded fallback
    """
    print("\n" + "="*50)
    print("FETCHING NIFTY 500 SYMBOLS (plain format)")
    print("="*50)

    symbols = None
    source  = None

    cache = load_cache()
    if cache:
        symbols = cache['symbols']
        source  = f"cache ({cache.get('source', 'unknown')})"

    if not symbols:
        symbols = fetch_from_nse()
        if symbols:
            source = "NSE Official API"
            save_cache(symbols, source)

    if not symbols:
        symbols = fetch_from_zerodha()
        if symbols:
            source = "Zerodha Instruments"
            save_cache(symbols, source)

    if not symbols:
        print("⚠️ All APIs failed — using hardcoded fallback")
        symbols = FALLBACK_SYMBOLS
        source  = f"Hardcoded ({len(FALLBACK_SYMBOLS)} stocks)"

    print(f"✅ {len(symbols)} symbols from: {source}")
    print("="*50 + "\n")

    # Return plain NSE symbols — NO Fyers prefix (e.g. "RELIANCE" not "NSE:RELIANCE-EQ")
    # Redis feed matches on plain symbol from meta_symbol field
    return [s.strip() for s in symbols if s and s.strip()]


if __name__ == "__main__":
    syms = get_nifty500_symbols()
    print(f"Total: {len(syms)}")
    print(f"First 10: {syms[:10]}")
    with open("nifty500_symbols.txt", "w") as f:
        f.write("\n".join(syms))
    print("Saved to nifty500_symbols.txt")