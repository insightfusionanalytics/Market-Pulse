"""
Quick Telegram test — run this now before market opens.
cd backend && python test_telegram.py
"""
import requests
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

#TG_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
#TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Telegram (NEW!)
TG_CHAT_ID=1004112832
TG_TOKEN="8449739735:AAHe4sFKkQ81nDyvImu9WMMTlMr5DwjUYfo"

print(f"Token  : {TG_TOKEN[:20] if TG_TOKEN else 'MISSING'}...")
print(f"Chat ID: {TG_CHAT_ID}")

url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
msg = (
    f"✅ <b>Telegram Test PASSED</b>\n"
    f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
    f"Chat ID: {TG_CHAT_ID}\n"
    f"Pre-Open Script ready for today's session."
)

r = requests.post(url, data={
    "chat_id": TG_CHAT_ID,
    "text": msg,
    "parse_mode": "HTML"
}, timeout=10)

print(f"\nStatus : {r.status_code}")
print(f"Response: {r.json()}")

if r.status_code == 200:
    print("\n✅ TELEGRAM WORKING — check your Telegram now")
else:
    print("\n❌ TELEGRAM FAILED — see error above")
    print("Most likely fix: Chat ID should be a number e.g. 1004112832")
    print("Make sure you have sent at least one message to your bot first")

    