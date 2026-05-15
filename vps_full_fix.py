"""
VPS FULL FIX SCRIPT
====================
1. Check AVAAIUSD real symbol position on exchange
2. Close if open
3. Reset DB
4. Stop bot, restart with fixed main.py
Run this ON VPS directly.
"""
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
        'User-Agent': 'BHARAT-FIX'
    }

db.load_secrets()

print("=" * 55)
print("  VPS FULL DIAGNOSTIC + FIX")
print("=" * 55)

# Show all configured symbols
print("\n[1] All symbols in DB:")
all_syms = db.get_all_symbols()
for s in all_syms:
    pos = db.get_symbol_position(s['symbol'])
    print(f"    Symbol={s['symbol']} | lots={s['lots']} | enabled={s['enabled']} | pos={pos}")

# Check ALL positions on exchange (not just BTC)
print("\n[2] ALL open positions on exchange:")
path  = "/v2/positions"
query = "?states=open"
try:
    hdrs = get_headers("GET", path, query=query)
    r    = requests.get(f"{BASE_URL}{path}{query}", headers=hdrs, timeout=10)
    print(f"    HTTP: {r.status_code}")
    if r.status_code == 200:
        positions = r.json().get("result", [])
        print(f"    Total open positions: {len(positions)}")
        for p in positions:
            sym  = (p.get("product", {}).get("symbol") or p.get("symbol") or "?")
            size = float(p.get("size", 0))
            entry= float(p.get("avg_entry_price", 0))
            upnl = float(p.get("unrealized_pnl", 0))
            pid  = p.get("product_id", "?")
            print(f"    {sym}: size={size} entry={entry} uPnL={upnl:.4f} pid={pid}")
    else:
        print(f"    FAILED: {r.text[:200]}")
except Exception as e:
    print(f"    Exception: {e}")

# Now close AVAAIUSD specifically
print("\n[3] Closing AVAAIUSD position if any...")
SYMBOL = "AVAAIUSD"
ASSET  = "AVAA"  # underlying for AVAAIUSD

# Find product id
pid = None
try:
    resp = requests.get(f"{BASE_URL}/v2/products?contract_types=perpetual_futures", timeout=10)
    if resp.status_code == 200:
        for p in resp.json().get("result", []):
            if p.get("symbol", "").upper() == SYMBOL:
                pid = p.get("id")
                print(f"    FOUND {SYMBOL} -> product_id={pid}")
                break
    if not pid:
        # Try searching differently
        for p in resp.json().get("result", []):
            sym = p.get("symbol", "")
            if "AVAA" in sym.upper() or "AVAX" in sym.upper():
                print(f"    Related symbol found: {sym} -> pid={p.get('id')}")
except Exception as e:
    print(f"    Error: {e}")

# Get position for AVAAIUSD - try all possible underlying assets
raw_size = 0
for asset_try in ["AVAA", "AVAX", "AVA"]:
    query2 = f"?underlying_asset_symbol={asset_try}"
    try:
        hdrs2 = get_headers("GET", path, query=query2)
        r2    = requests.get(f"{BASE_URL}{path}{query2}", headers=hdrs2, timeout=10)
        if r2.status_code == 200:
            for p in r2.json().get("result", []):
                sym_chk = (p.get("product", {}).get("symbol") or "").upper()
                size = float(p.get("size", 0))
                if size != 0:
                    print(f"    FOUND position: {sym_chk} size={size} (tried asset={asset_try})")
                    if sym_chk == SYMBOL or "AVAA" in sym_chk:
                        raw_size = size
                        if not pid:
                            pid = p.get("product_id")
    except Exception as e:
        print(f"    asset={asset_try} error: {e}")

if raw_size == 0:
    print(f"    Exchange shows 0 for {SYMBOL}. DB cleanup only.")
    db.update_symbol_position(SYMBOL, "NONE", 0.0, 0, 0, 0)
    print(f"    DB cleared for {SYMBOL}.")
else:
    abs_size   = abs(int(raw_size))
    close_side = "sell" if raw_size > 0 else "buy"
    print(f"\n    CLOSING {abs_size} lots of {SYMBOL} ({close_side.upper()})...")
    if pid:
        payload_dict = {
            "product_id":  int(pid),
            "size":        abs_size,
            "side":        close_side,
            "order_type":  "market_order",
            "reduce_only": True
        }
        payload = json.dumps(payload_dict)
        hdrs3   = get_headers("POST", "/v2/orders", payload=payload)
        resp3   = requests.post(f"{BASE_URL}/v2/orders", headers=hdrs3, data=payload, timeout=10)
        print(f"    Close HTTP: {resp3.status_code}")
        if resp3.status_code in [200, 201]:
            print(f"    SUCCESS: Closed {abs_size} lots!")
        else:
            print(f"    FAILED: {resp3.text[:200]}")
    db.update_symbol_position(SYMBOL, "NONE", 0.0, 0, 0, 0)
    print(f"    DB cleared for {SYMBOL}.")

# Final DB state
print("\n[4] Final DB state:")
for s in db.get_all_symbols():
    pos = db.get_symbol_position(s['symbol'])
    print(f"    {s['symbol']}: pos={pos}")

print("\n" + "=" * 55)
print("  DONE. Now bot needs to be restarted.")
print("=" * 55)
