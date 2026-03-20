"""
Nifty 500 symbol list and pre-open scan logic.

Provides Fyers-formatted NSE symbols for the scanner universe.
Tomorrow: fetch full Nifty 500 from NSE website or Yahoo Finance list.
"""

# Top 50 stocks for pre-open scanner (expand to 500 later)
_NIFTY50_SYMBOLS = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "HINDUNILVR",
    "ITC",
    "SBIN",
    "BHARTIARTL",
    "BAJFINANCE",
    "ASIANPAINT",
    "MARUTI",
    "HCLTECH",
    "KOTAKBANK",
    "LT",
    "AXISBANK",
    "TITAN",
    "ULTRACEMCO",
    "SUNPHARMA",
    "WIPRO",
    "NESTLEIND",
    "TATASTEEL",
    "BAJAJFINSV",
    "POWERGRID",
    "NTPC",
    "ONGC",
    "M&M",
    "TECHM",
    "ADANIPORTS",
    "COALINDIA",
    "DIVISLAB",
    "DRREDDY",
    "GRASIM",
    "HINDALCO",
    "INDUSINDBK",
    "JSWSTEEL",
    "BRITANNIA",
    "CIPLA",
    "EICHERMOT",
    "SHREECEM",
    "BAJAJ-AUTO",
    "TATACONSUM",
    "ADANIENT",
    "APOLLOHOSP",
    "BPCL",
    "UPL",
    "HDFCLIFE",
    "SBILIFE",
    "HEROMOTOCO",
    "TATACONSUM",
]


def get_nifty500_symbols() -> list[str]:
    """
    Return the scanner universe as Fyers-formatted NSE equity symbols.

    Format: "NSE:{SYMBOL}-EQ" (e.g. "NSE:RELIANCE-EQ").
    Currently returns top 50 stocks; will expand to full Nifty 500 later.

    Returns:
        List of symbol strings, e.g. ["NSE:RELIANCE-EQ", "NSE:TCS-EQ", ...].
    """
    return [f"NSE:{s}-EQ" for s in _NIFTY50_SYMBOLS]


def get_symbol_count() -> int:
    """
    Return the number of symbols in the scanner universe.

    Returns:
        int: Currently 50; will be 500 when full Nifty 500 is loaded.
    """
    return 50


if __name__ == "__main__":
    import os

    symbols = get_nifty500_symbols()
    count = get_symbol_count()

    # Output to terminal
    print(f"Symbols ({count}):")
    for s in symbols:
        print(s)
    print()
    print(f"Count: {count}")

    # Save to file: pre-open-scanner/outputs/nifty500_symbols.txt
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    outputs_dir = os.path.join(project_root, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    out_path = os.path.join(outputs_dir, "nifty500_symbols.txt")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"Symbols ({count}):\n")
        for s in symbols:
            f.write(s + "\n")
        f.write("\nCount: %d\n" % count)

    print(f"\nOutput saved to: {out_path}")
