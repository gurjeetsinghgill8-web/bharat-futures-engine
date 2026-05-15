"""
BHARAT FUTURES EXECUTOR — Delta Exchange BTC Perpetual Futures
=================================================================
Strategy  : SuperTrend — FUTURES only
Entry     : BUY if ST bullish | SELL if ST bearish
Leverage  : Configurable (5x/10x/25x/50x/100x/200x)
Symbol    : BTCUSD Perpetual Future (product_id=27)
================================================================="""
import time
import hmac
import hashlib
import requests
import datetime
import json
import socket
import db
from utils import log_terminal, send_telegram_msg, send_trade_alert, send_close_alert

# --- Force IPv4 ---
import requests.packages.urllib3.util.connection as urllib3_cn
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

BASE_URL = "https://api.india.delta.exchange"
FALLBACK_URL = "https://api.delta.exchange"

# ── PER-SYMBOL EXECUTION LOCK ────────────────────────────────
# Prevents two simultaneous order submissions for the same symbol
# (e.g. rapid candle-tick + heartbeat both entering at once)
import threading
_symbol_exec_locks = {}     # { symbol: threading.Lock() }
_symbol_exec_lock_meta = threading.Lock()

def _get_exec_lock(symbol):
    """Returns (or creates) a per-symbol threading.Lock."""
    with _symbol_exec_lock_meta:
        if symbol not in _symbol_exec_locks:
            _symbol_exec_locks[symbol] = threading.Lock()
        return _symbol_exec_locks[symbol]

# ── LOT INTEGRITY CHECK STATE ─────────────────────────────────
_lot_check_last_run = 0      # epoch seconds of last check
LOT_CHECK_INTERVAL  = 900    # 15 minutes

# ── FUTURES PRODUCT SYMBOLS ──────────────────────────────────
# Delta Exchange perpetual futures symbols
FUTURES_SYMBOLS = {
    "BTC": "BTCUSD",    # BTC Perpetual Future
    "ETH": "ETHUSD",    # ETH Perpetual Future (optional)
}

def get_delta_auth_headers(method, path, payload="", query_string=""):
    api_key    = db.get_param('delta_api_key', '')
    api_secret = db.get_param('delta_api_secret', '')
    timestamp  = str(int(time.time()))
    signature_data = method + timestamp + path + query_string + payload
    signature = hmac.new(
        api_secret.encode('utf-8'),
        signature_data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return {
        'api-key':      api_key,
        'signature':    signature,
        'timestamp':    timestamp,
        'Content-Type': 'application/json',
        'User-Agent':   'BHARAT-FUTURES-ENGINE-V1'
    }

# ── GET BTC SPOT PRICE ───────────────────────────────────────
def get_btc_ltp():
    for base in [BASE_URL, FALLBACK_URL]:
        try:
            resp = requests.get(
                f"{base}/v2/tickers?underlying_asset_symbols=BTC",
                timeout=5
            )
            if resp.status_code == 200:
                for t in resp.json().get("result", []):
                    sp = float(t.get("spot_price") or t.get("underlying_price") or 0)
                    if sp > 0:
                        return sp
        except Exception as e:
            print(f"[LTP Error] {e}")
    return 0.0

# ── GET FUTURES PRODUCT ID ───────────────────────────────────
def get_futures_product_id(asset="BTC"):
    symbol = FUTURES_SYMBOLS.get(asset, f"{asset}USD")
    for base in [BASE_URL, FALLBACK_URL]:
        try:
            resp = requests.get(
                f"{base}/v2/products?contract_types=perpetual_futures&underlying_asset_symbols={asset}",
                timeout=10
            )
            if resp.status_code == 200:
                for p in resp.json().get("result", []):
                    if p.get("symbol", "").upper() == symbol.upper() or \
                       p.get("contract_type") == "perpetual_futures":
                        pid = p.get("id")
                        sym = p.get("symbol")
                        print(f"[FUTURES] Found: {sym} → PID={pid}")
                        return pid, sym
        except Exception as e:
            print(f"[PID Error] {e}")
    # Fallback: product_id=27 is BTCUSD perpetual on Delta India (confirmed)
    print(f"[PID] Using hardcoded fallback: BTCUSD id=27")
    return 27, "BTCUSD"

# ── SYNC FUTURES POSITION ───────────────────────────────────
def sync_futures_position():
    """Reads live futures position from Delta Exchange and updates DB."""
    api_key = db.get_param('delta_api_key', '')
    if not api_key:
        return False

    path  = "/v2/positions"
    query = "?underlying_asset_symbol=BTC"
    url   = f"{BASE_URL}{path}{query}"
    try:
        headers = get_delta_auth_headers("GET", path, query_string=query)
        resp    = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"[SYNC] Failed: {resp.status_code} {resp.text[:100]}")
            return False

        positions = resp.json().get("result", [])
        active_symbol    = "NONE"
        active_pid       = "NONE"
        active_direction = "NONE"
        active_size      = 0
        active_entry     = 0.0
        total_upnl       = 0.0

        for p in positions:
            size = float(p.get("size", 0))
            if size == 0:
                continue
            symbol  = p.get("product", {}).get("symbol") or p.get("symbol") or ""
            pid     = str(p.get("product_id") or "")
            upnl    = float(p.get("unrealized_pnl", 0))
            entry   = float(p.get("avg_entry_price", 0))
            # Direction: size > 0 = LONG (bought futures), size < 0 = SHORT (sold futures)
            direction = "BUY" if size > 0 else "SELL"

            active_symbol    = symbol
            active_pid       = pid
            active_direction = direction
            active_size      = abs(size)
            active_entry     = entry
            total_upnl      += upnl

        db.set_param("active_symbol",    active_symbol)
        db.set_param("active_pid",       active_pid)
        db.set_param("active_direction", active_direction)
        db.set_param("active_qty",       str(int(active_size)))
        db.set_param("active_entry_price", str(active_entry))
        db.set_param("unrealized_pnl",   str(round(total_upnl, 4)))

        if active_symbol != "NONE":
            db.set_param("local_trade_active", "YES")
        else:
            db.set_param("local_trade_active", "NO")

        return True
    except Exception as e:
        print(f"[SYNC EXCEPTION] {e}")
        return False

# ── SET LEVERAGE ────────────────────────────────────────────
def set_leverage(product_id, leverage):
    """
    Sets leverage for a futures product on Delta Exchange.
    leverage: integer (5, 10, 25, 50, 100, 200)
    """
    api_key = db.get_param('delta_api_key', '')
    if not api_key:
        return False
    try:
        path    = f"/v2/products/{product_id}/orders/leverage"
        payload_dict = {"product_id": int(product_id), "leverage": str(leverage)}
        payload = json.dumps(payload_dict)
        headers = get_delta_auth_headers("POST", path, payload=payload)
        resp    = requests.post(f"{BASE_URL}{path}", headers=headers, data=payload, timeout=10)
        if resp.status_code in [200, 201]:
            print(f"[LEVERAGE] Set to {leverage}x for product {product_id}")
            return True
        else:
            print(f"[LEVERAGE] Failed: {resp.status_code} {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"[LEVERAGE ERROR] {e}")
        return False

# ── EXECUTE FUTURES ENTRY ────────────────────────────────────
def execute_futures_trade(asset, direction):
    """
    Opens a BTC Futures position.
    direction = "BUY"  → Open LONG  (price above anchor)
    direction = "SELL" → Open SHORT (price below anchor)
    """
    mode = "LIVE"
    qty  = int(db.get_param('trade_size', '1'))

    pid, symbol = get_futures_product_id(asset)
    if not pid:
        log_terminal(f"ERROR: Could not find Futures product for {asset}", "ERROR")
        return False

    side     = "buy" if direction == "BUY" else "sell"
    leverage = int(db.get_param('leverage', '10') or '10')
    log_terminal(f"FUTURES ENTRY: {side.upper()} {qty} x {symbol} @ market | Leverage={leverage}x", "TRADE")

    if mode == "LIVE":
        # Set leverage BEFORE placing order
        set_leverage(pid, leverage)
        try:
            payload_dict = {
                "product_id": int(pid),
                "size":       qty,
                "side":       side,
                "order_type": "market_order"
            }
            payload = json.dumps(payload_dict)
            headers = get_delta_auth_headers("POST", "/v2/orders", payload=payload)
            resp = requests.post(
                f"{BASE_URL}/v2/orders",
                headers=headers,
                data=payload,
                timeout=10
            )
            if resp.status_code in [200, 201]:
                log_terminal(f"✅ FUTURES ENTRY SUCCESS: {side.upper()} {qty} x {symbol}", "TRADE")
                send_telegram_msg(
                    f"🚀 FUTURES ENTRY\n"
                    f"Action   : {side.upper()}\n"
                    f"Symbol   : {symbol}\n"
                    f"Qty      : {qty}\n"
                    f"Leverage : {leverage}x\n"
                    f"Mode     : LIVE"
                )
                db.set_param("local_trade_active", "YES")
                db.set_param("active_symbol",    symbol)
                db.set_param("active_pid",       str(pid))
                db.set_param("active_direction", direction)
                db.set_param("active_qty",       str(qty))
                time.sleep(1)
                sync_futures_position()
                return True
            else:
                log_terminal(f"ENTRY FAILED: {resp.status_code} — {resp.text[:200]}", "ERROR")
                return False
        except Exception as e:
            log_terminal(f"ENTRY EXCEPTION: {e}", "ERROR")
            return False
    else:
        # PAPER TRADE
        ltp = get_btc_ltp()
        log_terminal(f"PAPER ENTRY: {side.upper()} {qty} x {symbol} @ {ltp:.0f}", "TRADE")
        db.set_param("local_trade_active", "YES")
        db.set_param("active_symbol",    symbol)
        db.set_param("active_pid",       str(pid or "PAPER"))
        db.set_param("active_direction", direction)
        db.set_param("active_qty",       str(qty))
        db.set_param("active_entry_price", str(ltp))
        send_telegram_msg(
            f"📝 PAPER ENTRY\n"
            f"Action   : {side.upper()}\n"
            f"Symbol   : {symbol}\n"
            f"Qty      : {qty}\n"
            f"Leverage : {leverage}x (paper)\n"
            f"Price    : {ltp:,.0f}"
        )
        return True

# ── SQUARE OFF ALL FUTURES ───────────────────────────────────
def square_off_futures(target_pid=None, reason="Manual"):
    """Closes all open futures positions (or specific PID)."""
    mode = "LIVE"
    log_terminal(f"SQUARE OFF TRIGGERED: reason={reason}", "ALERT")

    if mode == "PAPER":
        entry_price  = float(db.get_param("active_entry_price", "0") or "0")
        direction    = db.get_param("active_direction", "NONE")
        ltp          = get_btc_ltp()
        qty          = int(db.get_param("active_qty", "1") or "1")
        pnl          = 0.0
        if entry_price > 0 and ltp > 0 and direction != "NONE":
            if direction == "BUY":
                pnl = (ltp - entry_price) * qty
            else:
                pnl = (entry_price - ltp) * qty
        symbol = db.get_param("active_symbol", "BTCUSD")
        db.log_trade(symbol, direction, entry_price, ltp, round(pnl, 4), qty, "CLOSED")
        _clear_position_db()
        send_telegram_msg(
            f"✅ PAPER SQUARE OFF\n"
            f"Symbol : {symbol}\n"
            f"PnL    : ${pnl:+.2f}\n"
            f"Reason : {reason}"
        )
        return True

    # LIVE MODE
    pids_to_close = []
    if target_pid:
        pids_to_close = [str(target_pid)]
    else:
        for asset in ["BTC"]:
            try:
                path  = "/v2/positions"
                query = f"?underlying_asset_symbol={asset}"
                url   = f"{BASE_URL}{path}{query}"
                hdrs  = get_delta_auth_headers("GET", path, query_string=query)
                resp  = requests.get(url, headers=hdrs, timeout=10)
                if resp.status_code == 200:
                    for p in resp.json().get("result", []):
                        sz = float(p.get("size", 0))
                        if sz != 0:
                            pid = str(p.get("product_id") or "")
                            if pid:
                                pids_to_close.append(pid)
            except Exception as e:
                log_terminal(f"Square-off search error: {e}", "ERROR")

    if not pids_to_close:
        _clear_position_db()
        return True

    for pid in pids_to_close:
        try:
            # Re-fetch size and direction
            path  = "/v2/positions"
            query = "?underlying_asset_symbol=BTC"
            r     = requests.get(f"{BASE_URL}{path}{query}",
                                 headers=get_delta_auth_headers("GET", path, query_string=query),
                                 timeout=10)
            raw_size = 0
            if r.status_code == 200:
                for p in r.json().get("result", []):
                    if str(p.get("product_id")) == pid:
                        raw_size = float(p.get("size", 0))
                        break
            if raw_size == 0:
                continue
            close_side = "sell" if raw_size > 0 else "buy"
            abs_size   = abs(raw_size)
            payload_dict = {
                "product_id": int(pid),
                "size":       int(abs_size),
                "side":       close_side,
                "order_type": "market_order",
                "reduce_only": True
            }
            payload = json.dumps(payload_dict)
            resp2   = requests.post(
                f"{BASE_URL}/v2/orders",
                headers=get_delta_auth_headers("POST", "/v2/orders", payload=payload),
                data=payload,
                timeout=10
            )
            if resp2.status_code in [200, 201]:
                log_terminal(f"✅ CLOSED: PID {pid} ({close_side})", "TRADE")
                send_telegram_msg(f"✅ FUTURES CLOSED: PID {pid}\nReason: {reason}")
            else:
                log_terminal(f"CLOSE FAILED: {resp2.status_code} — {resp2.text[:100]}", "ERROR")
        except Exception as e:
            log_terminal(f"Close exception: {e}", "ERROR")

    _clear_position_db()
    return True

def _clear_position_db():
    db.set_param("local_trade_active", "NO")
    db.set_param("active_symbol",    "NONE")
    db.set_param("active_pid",       "NONE")
    db.set_param("active_direction", "NONE")
    db.set_param("active_qty",       "0")
    db.set_param("active_entry_price", "0")
    db.set_param("unrealized_pnl",   "0")


# ══════════════════════════════════════════════════════════════
# BRICK 2 — Multi-Symbol Functions (New additions below)
# Existing functions above are NEVER modified.
# ══════════════════════════════════════════════════════════════

def fetch_available_futures_symbols():
    """
    Fetches all perpetual futures symbols from Delta Exchange.
    Returns a sorted list of symbol strings e.g. ["BTCUSD", "ETHUSD", ...]
    Used by the dashboard dropdown when adding a new symbol.
    """
    result = []
    for base in [BASE_URL, FALLBACK_URL]:
        try:
            resp = requests.get(
                f"{base}/v2/products?contract_types=perpetual_futures",
                timeout=10
            )
            if resp.status_code == 200:
                for p in resp.json().get("result", []):
                    sym = p.get("symbol", "")
                    if sym:
                        result.append(sym.upper())
                if result:
                    result = sorted(set(result))
                    print(f"[SYMBOLS] Fetched {len(result)} futures symbols from {base}")
                    return result
        except Exception as e:
            print(f"[SYMBOLS] fetch error from {base}: {e}")
    print("[SYMBOLS] Could not fetch symbol list from Delta Exchange")
    return ["BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "BNBUSD"]  # safe fallback



def get_product_id_for_symbol(delta_symbol):
    """
    Returns (product_id, symbol) for any Delta Exchange perpetual symbol.
    Falls back to None if not found.
    """
    for base in [BASE_URL, FALLBACK_URL]:
        try:
            resp = requests.get(
                f"{base}/v2/products?contract_types=perpetual_futures",
                timeout=10
            )
            if resp.status_code == 200:
                for p in resp.json().get("result", []):
                    if p.get("symbol", "").upper() == delta_symbol.upper():
                        pid = p.get("id")
                        sym = p.get("symbol")
                        print(f"[SYMBOLS] {sym} → PID={pid}")
                        return pid, sym
        except Exception as e:
            print(f"[SYMBOLS] product_id lookup error: {e}")
    print(f"[SYMBOLS] Could not find PID for {delta_symbol}")
    return None, delta_symbol


def sync_position_for_symbol(delta_symbol):
    """
    Syncs the live exchange position for ONE symbol into the
    symbol_positions table (BRICK 1).

    ROOT CAUSE FIX:
    Old code: extracted asset by removing 'USD' (BBUSD → 'BB')
    Delta Exchange doesn't recognise 'BB' as an underlying asset.
    API returned empty list → bot always saw FLAT → re-entered every candle.

    New code: fetches ALL open positions, matches by EXACT symbol name.
    Works for BBUSD, COAIUSD, INJUSD — any symbol, no extraction needed.
    """
    api_key = db.get_param("delta_api_key", "")
    if not api_key:
        return False

    path  = "/v2/positions/margined"   # fetch ALL open positions at once
    query = ""
    try:
        hdrs = get_delta_auth_headers("GET", path, query_string=query)
        resp = requests.get(f"{BASE_URL}{path}", headers=hdrs, timeout=10)

        # Fallback to /v2/positions if margined endpoint unavailable
        if resp.status_code not in [200, 201]:
            path  = "/v2/positions"
            query = ""
            hdrs  = get_delta_auth_headers("GET", path, query_string=query)
            resp  = requests.get(f"{BASE_URL}{path}", headers=hdrs, timeout=10)

        if resp.status_code not in [200, 201]:
            print(f"[SYNC:{delta_symbol}] Both position endpoints failed: {resp.status_code}")
            return False

        direction  = "NONE"
        entry_px   = 0.0
        qty        = 0
        active_int = 0

        for p in resp.json().get("result", []):
            # Match by EXACT symbol name — no asset extraction
            sym_chk = (
                p.get("product", {}).get("symbol") or
                p.get("symbol") or ""
            ).upper()
            if sym_chk != delta_symbol.upper():
                continue
            size = float(p.get("size", 0))
            if size == 0:
                continue
            direction  = "BUY" if size > 0 else "SELL"
            entry_px   = float(p.get("avg_entry_price", 0))
            qty        = abs(int(size))
            active_int = 1
            print(f"[SYNC:{delta_symbol}] Found: {direction} {qty} lots @ {entry_px}")
            break

        if active_int == 0:
            print(f"[SYNC:{delta_symbol}] No open position on exchange — FLAT")

        db.update_symbol_position(
            delta_symbol,
            direction=direction,
            entry_price=entry_px,
            qty=qty,
            active=active_int,
            last_candle_ts=int(
                db.get_symbol_position(delta_symbol)["last_candle_ts"]
                if db.get_symbol_position(delta_symbol) else 0
            )
        )
        return True
    except Exception as e:
        print(f"[SYNC:{delta_symbol}] Exception: {e}")
        return False



def execute_trade_for_symbol(delta_symbol, direction, lots, leverage=10):
    """
    Opens a futures position for ANY symbol.
    direction = "BUY" (long) or "SELL" (short)
    Uses mode from DB (PAPER / LIVE) just like the existing BTC function.
    Writes result to symbol_positions table (BRICK 1).

    SAFETY GUARDS BUILT IN:
    1. Per-symbol execution lock (prevents concurrent duplicate orders)
    2. Pre-flight exchange check: if position already exists in THIS direction,
       skip entry entirely (belt-and-suspenders against the loop guard)
    3. Pre-flight direction sanity: if existing position is in OPPOSITE direction,
       log a warning — caller must close first.
    """
    exec_lock = _get_exec_lock(delta_symbol)
    if not exec_lock.acquire(blocking=False):
        log_terminal(f"[{delta_symbol}] EXECUTION LOCK HELD — skipping duplicate order.", "WARN")
        return False

    try:
        mode = "LIVE"
        pid, sym = get_product_id_for_symbol(delta_symbol)
        side = "buy" if direction == "BUY" else "sell"

        # ── PRE-FLIGHT: Check exchange LIVE position before ordering ──
        if mode == "LIVE":
            try:
                # Use all-positions endpoint (same fix as sync_position_for_symbol)
                r = requests.get(
                    f"{BASE_URL}/v2/positions",
                    headers=get_delta_auth_headers("GET", "/v2/positions", query_string=""),
                    timeout=8
                )
                if r.status_code == 200:
                    for p in r.json().get("result", []):
                        sym_chk = (p.get("product", {}).get("symbol") or "").upper()
                        if sym_chk != delta_symbol.upper():
                            continue
                        live_size = float(p.get("size", 0))
                        if abs(live_size) > 0:
                            live_dir = "BUY" if live_size > 0 else "SELL"
                            if live_dir == direction:
                                log_terminal(
                                    f"[{sym}] PRE-FLIGHT BLOCK: Already {live_size} lots {live_dir} on exchange. No new order.",
                                    "WARN"
                                )
                                sync_position_for_symbol(sym)
                                return False
                            else:
                                log_terminal(
                                    f"[{sym}] PRE-FLIGHT WARN: Exchange has {live_size} lots {live_dir}, but asked to {direction}. Close first!",
                                    "ALERT"
                                )
                                return False
            except Exception as pf_err:
                log_terminal(f"[{sym}] PRE-FLIGHT CHECK ERROR: {pf_err}", "WARN")
                # Continue anyway — don't block trading on a network hiccup

        log_terminal(
            f"[{sym}] ENTRY: {side.upper()} {lots} lots | Lev={leverage}x | Mode={mode}",
            "TRADE"
        )

        if mode == "LIVE":
            if pid:
                set_leverage(pid, leverage)
            try:
                payload_dict = {
                    "product_id": int(pid),
                    "size":       lots,
                    "side":       side,
                    "order_type": "market_order"
                }
                payload = json.dumps(payload_dict)
                hdrs    = get_delta_auth_headers("POST", "/v2/orders", payload=payload)
                resp    = requests.post(
                    f"{BASE_URL}/v2/orders", headers=hdrs, data=payload, timeout=10
                )
                if resp.status_code in [200, 201]:
                    log_terminal(f"[{sym}] ENTRY SUCCESS: {side.upper()} {lots} lots", "TRADE")
                    # COLOR-CODED Telegram alert
                    send_trade_alert(
                        symbol=sym, action=direction,
                        lots=lots, leverage=leverage, mode="LIVE"
                    )
                    db.update_symbol_position(
                        sym, direction=direction,
                        entry_price=0.0, qty=lots, active=1
                    )
                    import time as _time
                    _time.sleep(1)
                    sync_position_for_symbol(sym)
                    return True
                else:
                    log_terminal(f"[{sym}] ENTRY FAILED: {resp.status_code} {resp.text[:150]}", "ERROR")
                    return False
            except Exception as e:
                log_terminal(f"[{sym}] ENTRY EXCEPTION: {e}", "ERROR")
                return False
        else:
            # PAPER mode
            ltp = get_btc_ltp() if "BTC" in delta_symbol else 0.0
            try:
                resp_t = requests.get(
                    f"{BASE_URL}/v2/tickers/{delta_symbol}", timeout=5
                )
                if resp_t.status_code == 200:
                    ltp = float(
                        resp_t.json().get("result", {}).get("mark_price", ltp) or ltp
                    )
            except Exception:
                pass
            db.update_symbol_position(
                sym, direction=direction,
                entry_price=ltp, qty=lots, active=1
            )
            # COLOR-CODED PAPER alert
            send_trade_alert(
                symbol=sym, action=direction,
                lots=lots, leverage=leverage, mode="PAPER",
                extra=f"Price : {ltp:,.4f}"
            )
            return True

    finally:
        exec_lock.release()


def square_off_symbol(delta_symbol, reason="Manual"):
    """
    Closes the open position for ONE specific symbol.
    Writes to symbol_positions table (clears it).
    Does NOT affect other symbols or old BTC single-position params.
    """
    mode = "LIVE"
    pos  = db.get_symbol_position(delta_symbol)
    log_terminal(f"[{delta_symbol}] SQUARE OFF: reason={reason}", "ALERT")

    if mode == "PAPER":
        if pos and pos["active"]:
            entry_px  = pos["entry_price"]
            direction = pos["direction"]
            qty       = pos["qty"]
            ltp       = get_btc_ltp() if "BTC" in delta_symbol else entry_px
            try:
                resp_t = requests.get(
                    f"{BASE_URL}/v2/tickers/{delta_symbol}", timeout=5
                )
                if resp_t.status_code == 200:
                    ltp = float(
                        resp_t.json().get("result", {}).get("mark_price", ltp) or ltp
                    )
            except Exception:
                pass
            pnl = ((ltp - entry_px) * qty) if direction == "BUY" \
                  else ((entry_px - ltp) * qty)
            db.log_trade(delta_symbol, direction, entry_px, ltp, round(pnl, 4), qty, "CLOSED")
            send_close_alert(delta_symbol, reason=reason, pnl=round(pnl, 4), direction=direction)
        db.update_symbol_position(
            delta_symbol, direction="NONE",
            entry_price=0.0, qty=0, active=0
        )
        return True

    # LIVE mode
    # FIX: Do NOT use ?underlying_asset_symbol={asset} — asset extraction breaks
    # exotic symbols (e.g. BEATUSD → 'BEAT' not recognized by Delta).
    # Instead: fetch ALL positions and match by exact symbol name.
    pid, sym = get_product_id_for_symbol(delta_symbol)
    if not pid:
        db.update_symbol_position(delta_symbol, "NONE", 0.0, 0, 0)
        return False

    closed_dir = (pos["direction"] if pos else None)
    try:
        # Fetch ALL open positions — no broken asset extraction
        path  = "/v2/positions"
        hdrs  = get_delta_auth_headers("GET", path, query_string="")
        r     = requests.get(f"{BASE_URL}{path}", headers=hdrs, timeout=10)

        # Fallback to margined endpoint
        if r.status_code not in [200, 201]:
            path = "/v2/positions/margined"
            hdrs = get_delta_auth_headers("GET", path, query_string="")
            r    = requests.get(f"{BASE_URL}{path}", headers=hdrs, timeout=10)

        raw_size = 0
        if r.status_code == 200:
            for p in r.json().get("result", []):
                sym_chk = (
                    p.get("product", {}).get("symbol") or
                    p.get("symbol") or ""
                ).upper()
                if sym_chk == delta_symbol.upper():
                    raw_size   = float(p.get("size", 0))
                    closed_dir = "BUY" if raw_size > 0 else "SELL"
                    break

        if raw_size == 0:
            log_terminal(f"[{delta_symbol}] Already FLAT on exchange. Clearing DB.", "INFO")
            db.update_symbol_position(delta_symbol, "NONE", 0.0, 0, 0)
            return True

        close_side = "sell" if raw_size > 0 else "buy"
        payload_dict = {
            "product_id":  int(pid),
            "size":        int(abs(raw_size)),
            "side":        close_side,
            "order_type":  "market_order",
            "reduce_only": True
        }
        payload = json.dumps(payload_dict)
        resp2   = requests.post(
            f"{BASE_URL}/v2/orders",
            headers=get_delta_auth_headers("POST", "/v2/orders", payload=payload),
            data=payload, timeout=10
        )
        if resp2.status_code in [200, 201]:
            log_terminal(f"[{delta_symbol}] CLOSED OK ({close_side} {int(abs(raw_size))} lots)", "TRADE")
            send_close_alert(delta_symbol, reason=reason, direction=closed_dir)
        else:
            log_terminal(f"[{delta_symbol}] CLOSE FAILED: {resp2.status_code} — {resp2.text[:150]}", "ERROR")
    except Exception as e:
        log_terminal(f"[{delta_symbol}] CLOSE EXCEPTION: {e}", "ERROR")

    db.update_symbol_position(delta_symbol, "NONE", 0.0, 0, 0)
    return True



# ══════════════════════════════════════════════════════════════
# 3-MINUTE AUTO-CORRECTOR (Position Guardian)
# ══════════════════════════════════════════════════════════════
# Runs every 3 minutes. Fetches ALL positions in ONE API call.
# For each symbol: if lots > configured → CLOSE ALL EXCESS immediately.
# This is the last line of defense — catches any bug that slipped through.
# ══════════════════════════════════════════════════════════════
_lot_check_last_run = 0
LOT_CHECK_INTERVAL  = 180    # 3 minutes (was 900 = 15 min)


def check_symbol_lot_integrity():
    """
    3-minute position guardian. For each enabled symbol:
      1. Fetch ALL live positions from exchange in ONE call (no asset extraction bug).
      2. If live_lots > configured_lots → CLOSE entire position immediately.
         Bot will cleanly re-enter on next candle with correct lot size.
      3. If live_lots == 0 but DB says active → reset DB (zombie clear).
      4. If live_lots == configured_lots → just sync DB. All good.
    Sends Telegram alert on any correction action.
    """
    global _lot_check_last_run

    now = time.time()
    if now - _lot_check_last_run < LOT_CHECK_INTERVAL:
        return   # Not time yet — check every 3 minutes
    _lot_check_last_run = now

    mode = "LIVE"
    if mode == "PAPER":
        return

    api_key = db.get_param("delta_api_key", "")
    if not api_key:
        return

    symbols = db.get_all_symbols()
    enabled = [s for s in symbols if s["enabled"]]
    if not enabled:
        return

    log_terminal("[GUARDIAN] Running 3-min position integrity check...", "INFO")

    # ── Fetch ALL open positions in ONE call (no broken asset extraction) ──
    try:
        hdrs = get_delta_auth_headers("GET", "/v2/positions", query_string="")
        resp = requests.get(f"{BASE_URL}/v2/positions", headers=hdrs, timeout=10)
        if resp.status_code != 200:
            log_terminal(f"[GUARDIAN] Position fetch failed: {resp.status_code}", "WARN")
            return
        all_positions = {
            (p.get("product", {}).get("symbol") or "").upper(): p
            for p in resp.json().get("result", [])
            if abs(float(p.get("size", 0))) > 0
        }
    except Exception as e:
        log_terminal(f"[GUARDIAN] Fetch exception: {e}", "WARN")
        return

    for sym_cfg in enabled:
        symbol   = sym_cfg["symbol"].upper()
        cfg_lots = sym_cfg["lots"]

        try:
            live_pos  = all_positions.get(symbol)
            live_size = float(live_pos.get("size", 0)) if live_pos else 0.0
            abs_live  = abs(int(live_size))
            live_dir  = "BUY" if live_size > 0 else ("SELL" if live_size < 0 else "NONE")

            # ── Case 1: EXCESS LOTS — close ALL immediately ────────────
            if abs_live > cfg_lots:
                log_terminal(
                    f"[GUARDIAN:{symbol}] 🚨 EXCESS LOTS: "
                    f"Exchange={abs_live} | Configured={cfg_lots} | "
                    f"Closing ALL now!",
                    "ALERT"
                )
                send_telegram_msg(
                    f"🚨 <b>AUTO-CORRECTING {symbol}</b>\n"
                    f"{'─'*28}\n"
                    f"Exchange lots : <b>{abs_live}</b> ({live_dir})\n"
                    f"Configured    : <b>{cfg_lots}</b>\n"
                    f"Action        : Closing ALL → re-entering on next candle",
                    parse_mode="HTML"
                )
                pid, _ = get_product_id_for_symbol(symbol)
                if pid:
                    close_side = "sell" if live_size > 0 else "buy"
                    payload_dict = {
                        "product_id":  int(pid),
                        "size":        abs_live,
                        "side":        close_side,
                        "order_type":  "market_order",
                        "reduce_only": True
                    }
                    payload = json.dumps(payload_dict)
                    hdrs2 = get_delta_auth_headers("POST", "/v2/orders", payload=payload)
                    r2 = requests.post(
                        f"{BASE_URL}/v2/orders",
                        headers=hdrs2, data=payload, timeout=10
                    )
                    if r2.status_code in [200, 201]:
                        log_terminal(
                            f"[GUARDIAN:{symbol}] ✅ Closed {abs_live} lots. "
                            f"Will re-enter {cfg_lots} lot(s) next candle.",
                            "TRADE"
                        )
                        send_telegram_msg(
                            f"✅ <b>AUTO-CORRECTED {symbol}</b>\n"
                            f"Closed <b>{abs_live}</b> excess lots.\n"
                            f"Re-entering <b>{cfg_lots}</b> lot(s) on next candle.",
                            parse_mode="HTML"
                        )
                    else:
                        log_terminal(
                            f"[GUARDIAN:{symbol}] ❌ Close FAILED: {r2.status_code}",
                            "ERROR"
                        )
                # Always reset DB after close attempt
                db.update_symbol_position(symbol, "NONE", 0.0, 0, 0, 0)
                # Reset candle ts so bot re-enters on next candle
                db.set_param(f"candle_ts_{symbol}", "0")

            # ── Case 2: CORRECT SIZE — sync DB and continue ────────────
            elif abs_live == cfg_lots:
                # Position is exactly the right size — just sync DB
                sync_position_for_symbol(symbol)
                log_terminal(
                    f"[GUARDIAN:{symbol}] ✅ OK — Exchange={abs_live} lots {live_dir} | "
                    f"Configured={cfg_lots}. DB synced.",
                    "INFO"
                )

            else:
                # abs_live == 0 — exchange is flat
                db_pos = db.get_symbol_position(symbol)
                if db_pos and db_pos["active"]:
                    log_terminal(
                        f"[GUARDIAN:{symbol}] 🧹 ZOMBIE: DB=active but Exchange=FLAT. Clearing DB.",
                        "ALERT"
                    )
                    db.update_symbol_position(symbol, "NONE", 0.0, 0, 0, 0)
                    send_telegram_msg(
                        f"🧹 ZOMBIE CLEARED: {symbol}\n"
                        f"Exchange was FLAT but DB showed active. DB reset."
                    )
                else:
                    log_terminal(
                        f"[GUARDIAN:{symbol}] OK — FLAT on both exchange and DB.",
                        "INFO"
                    )

        except Exception as e:
            log_terminal(f"[LOT CHECK:{symbol}] Error: {e}", "ERROR")
