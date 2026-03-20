"""
Test Fyers connection before tomorrow's run
"""

import os
import time
from dotenv import load_dotenv
from fyers_feed import FyersDataFeed

load_dotenv(".env")

print("="*60)
print("FYERS CONNECTION TEST")
print("="*60)

app_id = os.getenv("FYERS_APP_ID")
access_token = os.getenv("FYERS_ACCESS_TOKEN")

print(f"\nApp ID: {app_id}")
print(f"Token: {access_token[:30]}... (truncated)")

print("\nConnecting to Fyers (LIVE mode)...")

feed = FyersDataFeed(
    app_id=app_id,
    access_token=access_token,
    symbols=["NSE:RELIANCE-EQ", "NSE:TCS-EQ"],
    mock_mode=False
)

feed.connect()
time.sleep(5)

status = feed.get_connection_status()
data = feed.get_live_data()

print("\n" + "="*60)
if status['connected'] and data:
    print("✅ SUCCESS! CONNECTION WORKING!")
    print("="*60)
    print("\nSample data:")
    for symbol, tick in list(data.items())[:2]:
        print(f"  {symbol}: LTP=₹{tick.get('ltp', 0):,.2f}, Change={tick.get('change_pct', 0):+.2f}%")
    print("\n✅ READY FOR TOMORROW!")
else:
    print("❌ FAILED! CONNECTION NOT WORKING")
    print("="*60)
    print(f"Status: {status}")

feed.disconnect()
