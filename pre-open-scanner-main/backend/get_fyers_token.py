"""
Generate Fyers access token from auth code
Run this script to get a fresh access token

SMART VERSION: Paste full URL or just auth_code - both work!
"""

from fyers_apiv3 import fyersModel
from urllib.parse import urlparse, parse_qs

# Hardcoded credentials (Day1.1 app - NEVER CHANGE THESE!)
APP_ID = "OJH52PHNOP-100"
SECRET_KEY = "5G7VSICZUL"
REDIRECT_URI = "https://www.google.com"

def extract_auth_code(input_string):
    """
    Smart function: Extract auth_code from either:
    1. Full URL: https://www.google.com/?auth_code=XXX&state=YYY
    2. Just the auth_code: XXX
    """
    input_string = input_string.strip()
    
    # Check if it's a URL (contains http:// or https://)
    if input_string.startswith('http://') or input_string.startswith('https://'):
        # Parse URL and extract auth_code parameter
        parsed = urlparse(input_string)
        params = parse_qs(parsed.query)
        
        if 'auth_code' in params:
            auth_code = params['auth_code'][0]
            print(f"✓ Detected full URL. Extracted auth_code.")
            return auth_code
        else:
            print("❌ URL provided but no 'auth_code' parameter found!")
            return None
    else:
        # Assume it's just the auth_code
        print(f"✓ Detected raw auth_code.")
        return input_string

print("="*60)
print("FYERS TOKEN GENERATOR (SMART VERSION)")
print("="*60)
print(f"\nApp ID: {APP_ID}")
print(f"Redirect URI: {REDIRECT_URI}")
print("\n1. Open this URL in browser:")
print(f"https://api-t1.fyers.in/api/v3/generate-authcode?client_id={APP_ID}&redirect_uri={REDIRECT_URI}&response_type=code&state=sample_state")
print("\n2. Login to Fyers and get redirected to Google")
print("\n3. You can paste EITHER:")
print("   - Full URL: https://www.google.com/?auth_code=XXX&state=YYY")
print("   - Just auth_code: XXX")

user_input = input("\nPaste here: ").strip()

# Smart extraction
auth_code = extract_auth_code(user_input)

if not auth_code:
    print("\n❌ Failed to extract auth_code. Please try again.")
    exit(1)

print("\nGenerating access token...")

try:
    session = fyersModel.SessionModel(
        client_id=APP_ID,
        secret_key=SECRET_KEY,
        redirect_uri=REDIRECT_URI,
        response_type='code',
        grant_type='authorization_code'
    )
    
    session.set_token(auth_code)
    response = session.generate_token()
    
    if 'access_token' in response:
        print("\n" + "="*60)
        print("✅ SUCCESS! ACCESS TOKEN GENERATED")
        print("="*60)
        print(f"\nAccess Token:\n{response['access_token']}")
        print("\n" + "="*60)
        print("📋 NEXT STEPS:")
        print("1. Copy the token above")
        print("2. Open backend/.env file")
        print("3. Update: FYERS_ACCESS_TOKEN=<paste token>")
        print("4. Update: MOCK_MODE=false")
        print("5. Save .env file")
        print("="*60)
    else:
        print("\n❌ Token generation failed!")
        print(f"Response: {response}")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nPossible issues:")
    print("1. Auth code expired (get new one)")
    print("2. Invalid auth code format")
    print("3. Network connection issue")
