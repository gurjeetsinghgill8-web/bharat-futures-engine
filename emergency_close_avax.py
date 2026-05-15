import sys, io, time, json, requests, socket, hmac, hashlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests.packages.urllib3.util.connection as urllib3_cn
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
import db

BASE_URL = "https://api.india.delta.exchange"

def get_headers(method, path, payload="", query=""):
    api_key    = db.get_param('delta_api_key', '')
    api_secret = db.get_param('delta_api_secret', '')
    ts         = str(int(time.time()))
    sig_data   = method + ts + path + query + payload
    sig = hmac.new(api_secret.encode(), sig_data.encode(), hashlib.sha256).hexdigest()
    return {
        'api-key': api_key, 'signature': sig,
        'timestamp': ts, 'Content-Type': 'application/json',
        'User-Agent': 'BHARAT-EMERGENCY'
    }

db.load_secrets()

SYMBOL = "AVAXUSD"
ASSET  = "AVAX"

print("=" * 55)
print("  AVAXUSD EMERGENCY DIAGNOSTIC + CLOSE")
print("=" * 55)

# Step 1: Find product ID
print("\n[1] Finding product_id for AVAXUSD...")
pid = None
try:
    resp = requests.get(f"{BASE_URL}/v2/products?contract_types=perpetual_futures", timeout=10)
    if resp.status_code == 200:
        for p in resp.json().get("result", []):
            if p.get("symbol", "").upper() == SYMBOL:
                pid = p.get("id")
                print(f"    FOUND: product_id = {pid}")
                break
    if not pid:
        print("    NOT FOUND in product list!")
except Exception as e:
    print(f"    Error: {e}")

# Step 2: Check live exchange position
print(f"\n[2] Checking LIVE exchange position for {SYMBOL}...")
path  = "/v2/positions"
query = f"?underlying_asset_symbol={ASSET}"
raw_size = 0
try:
    hdrs = get_headers("GET", path, query=query)
    r    = requests.get(f"{BASE_URL}{path}{query}", headers=hdrs, timeout=10)
    print(f"    HTTP Status: {r.status_code}")
    if r.status_code == 200:
        all_positions = r.json().get("result", [])
        print(f"    Total positions returned: {len(all_positions)}")
        for p in all_positions:
            sym_chk   = (p.get("product", {}).get("symbol") or "").upper()
            size      = float(p.get("size", 0))
            avg_entry = float(p.get("avg_entry_price", 0))
            upnl      = float(p.get("unrealized_pnl", 0))
            print(f"    Symbol={sym_chk} | size={size} | entry={avg_entry} | uPnL={upnl:.4f}")
            if sym_chk == SYMBOL:
                raw_size = size
    else:
        print(f"    FAILED: {r.text[:300]}")
except Exception as e:
    print(f"    Exception: {e}")

# Step 3: Check DB position
print(f"\n[3] DB position for {SYMBOL}:")
pos_db = db.get_symbol_position(SYMBOL)
print(f"    DB record: {pos_db}")

# Step 4: Close if needed
if raw_size == 0:
    print(f"\n    Exchange shows 0 lots for {SYMBOL}. No close needed.")
    if pos_db and pos_db.get("active"):
        print("    But DB says active=True! Clearing DB...")
        db.update_symbol_position(SYMBOL, direction="NONE", entry_price=0.0, qty=0, active=0, last_candle_ts=0)
        print("    DB cleared.")
else:
    abs_size   = abs(int(raw_size))
    close_side = "sell" if raw_size > 0 else "buy"
    direction  = "LONG" if raw_size > 0 else "SHORT"
    print(f"\n[4] CLOSING {direction} position: {abs_size} lots -> {close_side.upper()}")
    if not pid:
        print("    ABORT: No product_id found!")
    else:
        payload_dict = {
            "product_id":  int(pid),
            "size":        abs_size,
            "side":        close_side,
            "order_type":  "market_order",
            "reduce_only": True
        }
        payload = json.dumps(payload_dict)
        hdrs = get_headers("POST", "/v2/orders", payload=payload)
        resp2 = requests.post(f"{BASE_URL}/v2/orders", headers=hdrs, data=payload, timeout=10)
        print(f"    Close HTTP: {resp2.status_code}")
        if resp2.status_code in [200, 201]:
            oid = resp2.json().get("result", {}).get("id", "OK")
            print(f"    *** SUCCESS: Closed {abs_size} lots of {SYMBOL} ***")
            print(f"    Order ID: {oid}")
            # Clear DB
            db.update_symbol_position(SYMBOL, direction="NONE", entry_price=0.0, qty=0, active=0, last_candle_ts=0)
            print("    DB cleared.")
        else:
            print(f"    FAILED: {resp2.text[:300]}")

# Step 5: Show symbols table
print(f"\n[5] All symbols in DB (lots config):")
all_syms = db.get_all_symbols()
for s in all_syms:
    print(f"    {s}")

print("\n" + "=" * 55)
print("  DONE")
print("=" * 55)
