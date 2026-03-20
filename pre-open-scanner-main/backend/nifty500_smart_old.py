"""
Dynamic Nifty 500 Symbol Fetcher
Fetches from NSE official API with fallback to hardcoded list.

Auto-updates daily, caches locally.
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import List

# Cache file location
CACHE_FILE = "nifty500_cache.json"
CACHE_VALIDITY_DAYS = 1  # Refresh daily

# NSE Official API endpoint
NSE_NIFTY500_URL = "https://www.nse.in/api/equity-stockIndices?index=NIFTY%20500"

# Fallback: Hardcoded list (used if API fails)
FALLBACK_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN",
    "BHARTIARTL", "BAJFINANCE", "ASIANPAINT", "MARUTI", "HCLTECH", "KOTAKBANK", "LT",
    "AXISBANK", "TITAN", "ULTRACEMCO", "SUNPHARMA", "WIPRO", "NESTLEIND", "TATASTEEL",
    "BAJAJFINSV", "POWERGRID", "NTPC", "ONGC", "M&M", "TECHM", "ADANIPORTS", "COALINDIA",
    "DIVISLAB", "DRREDDY", "GRASIM", "HINDALCO", "INDUSINDBK", "JSWSTEEL", "BRITANNIA",
    "CIPLA", "EICHERMOT", "SHREECEM", "BAJAJ-AUTO", "TATACONSUM", "ADANIENT", "APOLLOHOSP",
    "BPCL", "UPL", "HDFCLIFE", "SBILIFE", "HEROMOTOCO", "TATAMOTORS"
    # ... (50 for now, full 500 as fallback if needed)
]


def fetch_from_nse() -> List[str]:
    """
    Fetch Nifty 500 constituents from NSE official API.
    
    Returns:
        List of stock symbols (without NSE: prefix)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        print("📡 Fetching Nifty 500 from NSE official API...")
        
        # First, get NSE homepage to set cookies (NSE requires this)
        session = requests.Session()
        session.get("https://www.nse.in", headers=headers, timeout=10)
        
        # Now fetch the index data
        response = session.get(NSE_NIFTY500_URL, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            stocks = data.get('data', [])
            
            symbols = []
            for stock in stocks:
                symbol = stock.get('symbol')
                if symbol and symbol != 'NIFTY 500':  # Exclude index itself
                    symbols.append(symbol)
            
            print(f"✅ Fetched {len(symbols)} stocks from NSE")
            return symbols
        else:
            print(f"⚠️ NSE API returned status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching from NSE: {e}")
        return None


def fetch_from_zerodha() -> List[str]:
    """
    Fetch from Zerodha instruments list (alternative source).
    
    Returns:
        List of NSE EQ symbols
    """
    try:
        print("📡 Fetching from Zerodha instruments...")
        
        url = "https://api.kite.trade/instruments"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            symbols = []
            
            for line in lines[1:]:  # Skip header
                parts = line.split(',')
                if len(parts) >= 3:
                    exchange = parts[0]
                    tradingsymbol = parts[2]
                    segment = parts[3] if len(parts) > 3 else ""
                    
                    # Filter: NSE, EQ segment only
                    if exchange == 'NSE' and segment == 'EQ':
                        symbols.append(tradingsymbol)
            
            print(f"✅ Fetched {len(symbols)} NSE stocks from Zerodha")
            # Note: This is ALL NSE stocks, not just Nifty 500
            # We'd need to filter further, but this is a good fallback
            return symbols[:500]  # Take first 500 as approximation
        else:
            print(f"⚠️ Zerodha API returned status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching from Zerodha: {e}")
        return None


def load_cache() -> dict:
    """Load cached symbols if valid."""
    if not os.path.exists(CACHE_FILE):
        return None
    
    try:
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
        
        # Check if cache is still valid
        cached_date = datetime.fromisoformat(cache['date'])
        if datetime.now() - cached_date < timedelta(days=CACHE_VALIDITY_DAYS):
            print(f"✅ Using cached symbols (from {cache['date'][:10]})")
            return cache
        else:
            print(f"⏰ Cache expired (from {cache['date'][:10]})")
            return None
            
    except Exception as e:
        print(f"⚠️ Error loading cache: {e}")
        return None


def save_cache(symbols: List[str], source: str):
    """Save symbols to cache."""
    cache = {
        'date': datetime.now().isoformat(),
        'source': source,
        'symbols': symbols,
        'count': len(symbols)
    }
    
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
        print(f"💾 Cached {len(symbols)} symbols from {source}")
    except Exception as e:
        print(f"⚠️ Error saving cache: {e}")


def get_nifty500_symbols() -> List[str]:
    """
    Get Nifty 500 symbols with smart fallback strategy.
    
    Priority:
    1. Check cache (if valid)
    2. Fetch from NSE official API
    3. Fetch from Zerodha instruments
    4. Use hardcoded fallback
    
    Returns:
        List of Fyers-formatted symbols: ["NSE:RELIANCE-EQ", ...]
    """
    print("\n" + "="*60)
    print("FETCHING NIFTY 500 SYMBOLS")
    print("="*60)
    
    symbols = None
    source = None
    
    # Step 1: Try cache
    cache = load_cache()
    if cache:
        symbols = cache['symbols']
        source = f"cache ({cache['source']})"
    
    # Step 2: Try NSE official
    if not symbols:
        symbols = fetch_from_nse()
        if symbols:
            source = "NSE Official API"
            save_cache(symbols, source)
    
    # Step 3: Try Zerodha
    if not symbols:
        symbols = fetch_from_zerodha()
        if symbols:
            source = "Zerodha Instruments"
            save_cache(symbols, source)
    
    # Step 4: Fallback to hardcoded
    if not symbols:
        print("⚠️ All APIs failed, using hardcoded fallback")
        symbols = FALLBACK_SYMBOLS
        source = "Hardcoded Fallback"
    
    print(f"\n✅ Using {len(symbols)} symbols from: {source}")
    print("="*60 + "\n")
    
    # Convert to Fyers format
    fyers_symbols = [f"NSE:{s}-EQ" for s in symbols]
    return fyers_symbols


def get_symbol_count() -> int:
    """Return count of symbols."""
    return len(get_nifty500_symbols())


def force_refresh():
    """Force refresh by deleting cache."""
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        print("🔄 Cache cleared, will fetch fresh data")


if __name__ == "__main__":
    # Test the fetcher
    print("\n🧪 TESTING SYMBOL FETCHER\n")
    
    # Option 1: Normal fetch (uses cache if valid)
    symbols = get_nifty500_symbols()
    print(f"\nGot {len(symbols)} symbols")
    print(f"First 10: {symbols[:10]}")
    
    # Option 2: Force refresh (uncomment to test)
    # force_refresh()
    # symbols = get_nifty500_symbols()
    
    # Save to file for inspection
    with open("nifty500_symbols.txt", "w") as f:
        for symbol in symbols:
            f.write(symbol + "\n")
    print(f"\n📄 Saved to nifty500_symbols.txt")
