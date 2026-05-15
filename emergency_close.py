"""
EMERGENCY CLOSE — BBUSD
Closes ALL open BBUSD lots right now.
Run once, then delete.
"""
import sys, json, time, hmac, hashlib, socket
import requests

# Force IPv4
import requests.packages.urllib3.util.connection as urllib3_cn
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

import db
db.load_secrets()

API_KEY    = db.get_param("delta_api_key", "")
API_SECRET = db.get_param("delta_api_secret", "")
BASE_URL   = "https://api.india.delta.exchange"

def auth_headers(method, path, payload=""):
    ts        = str(int(time.time()))
    sig_data  = method + ts + path + payload
    signature = hmac.new(API_SECRET.encode(), sig_data.encode(), hashlib.sha256).hexdigest()
    return {
        "api-key":        API_KEY,
        "timestamp":      ts,
        "signature":      signature,
        "Content-Type":   "application/json"
    }

print("=" * 50)
print("  EMERGENCY CLOSE — BBUSD")
print("=" * 50)

# Step 1: Get ALL positions
print("\n[1] Fetching all positions...")
hdrs = auth_headers("GET", "/v2/positions")
resp = requests.get(f"{BASE_URL}/v2/positions", headers=hdrs, timeout=10)
print(f"    Status: {resp.status_code}")

if resp.status_code != 200:
    print(f"    FAILED: {resp.text[:200]}")
    sys.exit(1)

bbusd_size = 0
bbusd_pid  = None

for p in resp.json().get("result", []):
    sym = (p.get("product", {}).get("symbol") or "").upper()
    sz  = float(p.get("size", 0))
    pid = p.get("product", {}).get("id")
    print(f"    Found: {sym} size={sz} pid={pid}")
    if sym == "BBUSD" and abs(sz) > 0:
        bbusd_size = sz
        bbusd_pid  = pid

if bbusd_size == 0:
    print("\n[!] BBUSD position not found or already flat.")
    # Reset DB anyway
    db.update_symbol_position("BBUSD", "NONE", 0.0, 0, 0, 0)
    db.set_param("candle_ts_BBUSD", "0")
    print("    DB reset done.")
    sys.exit(0)

abs_lots   = abs(int(bbusd_size))
close_side = "sell" if bbusd_size > 0 else "buy"

print(f"\n[2] BBUSD has {abs_lots} lots ({'LONG' if bbusd_size>0 else 'SHORT'})")
print(f"    Closing ALL {abs_lots} lots with {close_side.upper()} reduce_only...")

# Step 2: Get product ID if not found above
if not bbusd_pid:
    print("[3] Getting product ID for BBUSD...")
    r = requests.get(f"{BASE_URL}/v2/products?contract_types=perpetual_futures", timeout=10)
    for p in r.json().get("result", []):
        if p.get("symbol", "").upper() == "BBUSD":
            bbusd_pid = p.get("id")
            print(f"    PID = {bbusd_pid}")
            break

if not bbusd_pid:
    print("    ERROR: Cannot find BBUSD product ID!")
    sys.exit(1)

# Step 3: Place close order
payload_dict = {
    "product_id":  int(bbusd_pid),
    "size":        abs_lots,
    "side":        close_side,
    "order_type":  "market_order",
    "reduce_only": True
}
payload = json.dumps(payload_dict)
hdrs2   = auth_headers("POST", "/v2/orders", payload)
r2 = requests.post(f"{BASE_URL}/v2/orders", headers=hdrs2, data=payload, timeout=10)

print(f"\n[4] Close order response: {r2.status_code}")
if r2.status_code in [200, 201]:
    print(f"    ✅ SUCCESS — Closed {abs_lots} BBUSD lots!")
    # Reset DB
    db.update_symbol_position("BBUSD", "NONE", 0.0, 0, 0, 0)
    db.set_param("candle_ts_BBUSD", "0")
    print("    DB reset. Bot will re-enter correctly on next candle.")
else:
    print(f"    ❌ FAILED: {r2.text[:300]}")

print("\n" + "=" * 50)
print("  DONE. Now restart the bot.")
print("=" * 50)
