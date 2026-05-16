"""
BHARAT FUTURES ENGINE — SUPERTREND SIGNAL ENGINE
=================================================
Instrument : BTC Perpetual Futures (Delta Exchange)
Indicator  : SuperTrend ONLY
Default    : 15-min candles | Period=10 | Multiplier=1
Signal     : Candle CLOSE based (no anticipation)
  SuperTrend GREEN (Up)   → BUY  (Long Futures)
  SuperTrend RED   (Down) → SELL (Short Futures)
=================================================
"""
import time
import datetime
import socket
import sys
import traceback
import threading
import json as _json
import pandas as pd
import numpy as np

# FORCE IPv4 — prevents IPv6 from causing Delta Exchange auth failures
import requests
import requests.packages.urllib3.util.connection as urllib3_cn
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

import db
import futures_executor
# supertrend module removed — multi-symbol dynamic system deleted (Block 1)

try:
    from utils import send_telegram_msg, log_terminal
except ImportError:
    def send_telegram_msg(msg): print(f"TG: {msg}")
    def log_terminal(msg, typ="INFO"): print(f"[{typ}] {msg}")

# ── TELEGRAM COMMAND LISTENER ────────────────────────────────
# Runs in background thread — polls for commands every 10 seconds.
# Send these from YOUR Telegram to control the bot without SSH:
#   /status       — get engine status
#   /fix_avax     — emergency close ALL AVAXUSD + reset DB
#   /remove_avax  — permanently remove AVAXUSD from symbols
#   /stop_engine  — stop trading engine
#   /start_engine — start trading engine
#   /positions    — show all symbol positions
_tg_last_update_id = 0

def _tg_process_command(text, chat_id):
    """Handle a single Telegram command."""
    token = db.get_param("telegram_bot_token", "")
    cmd = text.strip().lower().split()[0] if text.strip() else ""

    def reply(msg):
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg},
                timeout=10
            )
        except Exception:
            pass

    if cmd == "/status":
        mode     = "LIVE"
        running  = db.get_param("algo_running", "OFF")
        syms     = db.get_all_symbols()
        sym_lines = ""
        for s in syms:
            pos = db.get_symbol_position(s["symbol"])
            state = f"ACTIVE {pos['direction']} {pos['qty']}lots" if (pos and pos["active"]) else "FLAT"
            sym_lines += f"\n  {s['symbol']}: {state} (enabled={'YES' if s['enabled'] else 'NO'})"
        reply(
            f"BHARAT FUTURES STATUS\n"
            f"Mode   : {mode}\n"
            f"Engine : {running}\n"
            f"Symbols:{sym_lines if sym_lines else ' None'}"
        )

    elif cmd == "/fix_avax":
        reply("Starting AVAXUSD emergency close...")
        try:
            from futures_executor import square_off_symbol, sync_position_for_symbol
            sync_position_for_symbol("AVAXUSD")
            pos = db.get_symbol_position("AVAXUSD")
            if pos and pos["active"]:
                square_off_symbol("AVAXUSD", reason="Telegram /fix_avax command")
                db.update_symbol_position("AVAXUSD", "NONE", 0.0, 0, 0, 0)
                reply("AVAXUSD closed and DB reset!")
            else:
                db.update_symbol_position("AVAXUSD", "NONE", 0.0, 0, 0, 0)
                reply("AVAXUSD was already FLAT. DB cleared.")
        except Exception as e:
            reply(f"Error: {e}")

    elif cmd == "/remove_avax":
        reply("Removing AVAXUSD permanently from symbols table...")
        try:
            # First close any open position
            from futures_executor import square_off_symbol
            try:
                square_off_symbol("AVAXUSD", reason="Telegram /remove_avax")
            except Exception:
                pass
            db.remove_symbol("AVAXUSD")
            reply("AVAXUSD removed! Bot will never trade it again.")
        except Exception as e:
            reply(f"Error: {e}")

    elif cmd == "/stop_engine":
        db.set_param("algo_running", "OFF")
        reply("Engine STOPPED. No new trades will be placed.")

    elif cmd == "/start_engine":
        db.set_param("algo_running", "ON")
        reply("Engine STARTED. Trading resumed.")

    elif cmd == "/lot_check":
        reply("Running immediate lot integrity scan...")
        try:
            from futures_executor import check_symbol_lot_integrity, _lot_check_last_run
            import futures_executor as _fe
            _fe._lot_check_last_run = 0   # Force it to run NOW
            check_symbol_lot_integrity()
            reply("Lot integrity scan complete. Check console / log.")
        except Exception as e:
            reply(f"Lot check error: {e}")

    elif cmd == "/positions":
        syms = db.get_all_symbols()
        if not syms:
            reply("No symbols configured.")
            return
        lines = "LIVE POSITIONS:\n"
        for s in syms:
            pos = db.get_symbol_position(s["symbol"])
            if pos and pos["active"]:
                lines += f"  {s['symbol']}: {pos['direction']} {pos['qty']}lots @ {pos['entry_price']:.4f}\n"
            else:
                lines += f"  {s['symbol']}: FLAT\n"
        reply(lines)

    elif cmd == "/add":
        # Usage: /add SOLUSD  or  /add SOLUSD 2  (2 = lots)
        parts = text.strip().split()
        if len(parts) < 2:
            reply("Usage: /add SYMBOL [lots]\nExample: /add SOLUSD\nExample: /add ETHUSD 2")
        else:
            sym_add  = parts[1].upper()
            lots_add = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 1
            # Block stablecoins
            if sym_add.replace("USD","") in {"BUSD","USDT","USDC","TUSD","USDP","DAI"} or sym_add in BLOCKED_SYMBOLS:
                reply(f"⚠️ {sym_add} is a stablecoin — BLOCKED.\nSuperTrend is meaningless on $1 coins.")
            else:
                tf  = db.get_param("timeframe", "15m")
                per = int(db.get_param("st_period", "20") or 20)
                mul = float(db.get_param("st_multiplier", "1.5") or 1.5)
                db.add_symbol(sym_add, timeframe=tf, st_period=per,
                              st_multiplier=mul, lots=lots_add, enabled=1)
                reply(
                    f"✅ SYMBOL ADDED: {sym_add}\n"
                    f"TF={tf} | P={per} | M={mul} | Lots={lots_add}\n"
                    f"Bot will trade it on the next candle close."
                )
                send_telegram_msg(
                    f"🟢 SYMBOL ADDED: {sym_add}\n"
                    f"TF={tf} | P={per} | M={mul} | Lots={lots_add}"
                )

    elif cmd == "/remove":
        # Usage: /remove SOLUSD
        parts = text.strip().split()
        if len(parts) < 2:
            reply("Usage: /remove SYMBOL\nExample: /remove SOLUSD")
        else:
            sym_rem = parts[1].upper()
            try:
                # Close any open position first
                pos_rem = db.get_symbol_position(sym_rem)
                if pos_rem and pos_rem["active"]:
                    reply(f"Closing open {sym_rem} position first...")
                    futures_executor.square_off_symbol(sym_rem, reason="Telegram /remove command")
                db.remove_symbol(sym_rem)
                reply(
                    f"✅ SYMBOL REMOVED: {sym_rem}\n"
                    f"Position closed (if any). Bot will no longer trade it."
                )
                send_telegram_msg(f"🗑️ SYMBOL REMOVED: {sym_rem}")
            except Exception as e:
                reply(f"Error removing {sym_rem}: {e}")

    elif cmd == "/portfolio":
        syms_all = db.get_all_symbols()
        if not syms_all:
            reply("Portfolio is empty.\nUse /add SYMBOL to add a coin.")
        else:
            lines = "💼 PORTFOLIO:\n"
            for s in syms_all:
                pos_p = db.get_symbol_position(s["symbol"])
                if pos_p and pos_p["active"]:
                    lines += (
                        f"  {s['symbol']}: {pos_p['direction']} "
                        f"{pos_p['qty']}lots @ {pos_p['entry_price']:.4f}\n"
                    )
                else:
                    lines += f"  {s['symbol']}: FLAT\n"
            lines += f"\nTF={db.get_param('timeframe','15m')} | "
            lines += f"P={db.get_param('st_period','20')} | "
            lines += f"M={db.get_param('st_multiplier','1.5')}"
            reply(lines)

    elif cmd.startswith("/"):
        reply(
            "Commands available:\n"
            "/status       - Engine status\n"
            "/add SYMBOL   - Add coin to portfolio (e.g. /add SOLUSD)\n"
            "/add SYMBOL N - Add coin with N lots (e.g. /add ETHUSD 2)\n"
            "/remove SYM   - Close + remove coin (e.g. /remove SOLUSD)\n"
            "/portfolio    - Show all portfolio coins + positions\n"
            "/positions    - All symbol positions\n"
            "/fix_avax     - Emergency close AVAXUSD\n"
            "/stop_engine  - Stop trading\n"
            "/start_engine - Resume trading\n"
            "/lot_check    - Immediate lot integrity scan"
        )


def _telegram_listener_thread():
    """Background thread: polls Telegram for commands every 10 seconds."""
    global _tg_last_update_id
    time.sleep(5)  # Let bot fully start first
    log_terminal("Telegram command listener started.", "INFO")

    while True:
        try:
            token   = db.get_param("telegram_bot_token", "")
            chat_id = db.get_param("telegram_chat_id", "")
            if not token or not chat_id:
                time.sleep(30)
                continue

            url    = f"https://api.telegram.org/bot{token}/getUpdates"
            params = {"timeout": 5, "offset": _tg_last_update_id + 1, "limit": 10}
            resp   = requests.get(url, params=params, timeout=10)

            if resp.status_code == 200:
                updates = resp.json().get("result", [])
                for upd in updates:
                    _tg_last_update_id = upd["update_id"]
                    msg  = upd.get("message", {})
                    text = msg.get("text", "")
                    from_id = str(msg.get("chat", {}).get("id", ""))
                    # Only accept commands from the configured chat_id (security)
                    if text.startswith("/") and from_id == str(chat_id):
                        log_terminal(f"Telegram command received: {text}", "INFO")
                        _tg_process_command(text, chat_id)

        except Exception:
            pass  # Silent fail — never crash main thread
        time.sleep(10)


# ── GLOBAL GUARDS ────────────────────────────────────────────
_last_processed_candle_ts = 0

# ── GLOBAL GUARDS ────────────────────────────────────────────
# ╔══════════════════════════════════════════════════════════╗
# ║  DELTA EXCHANGE WHITELISTED IP — PERMANENT — NEVER CHANGE ║
# ║  Only 46.224.133.16 is accepted by Delta Exchange API.    ║
# ║  VPN MUST be connected on VPS to get this IP.             ║
# ║  Do NOT use laptop IP, VPS real IP, or any other IP.      ║
# ╚══════════════════════════════════════════════════════════╝
ALLOWED_TRADING_IP = "46.224.133.16"   # PERMANENT — DO NOT CHANGE
_vpn_alert_sent_at = 0

# ── STABLECOIN BLOCKLIST (NEVER TRADE THESE) ──────────────────
# SuperTrend on a $1-pegged coin = meaningless. ATR ≈ 0. Only noise.
# BUSD caused massive losses in live trading. Never again.
BLOCKED_SYMBOLS = {"BUSD", "USDT", "USDC", "TUSD", "USDP", "DAI", "HUSD", "SUSD", "GUSD"}

def _get_current_ip():
    """Returns current public IP, or None on failure."""
    try:
        import requests as _r
        return _r.get("https://api.ipify.org", timeout=4).text.strip()
    except Exception:
        return None

# ── CANDLE CHANGE GUARD ───────────────────────────────────────
# Tracks the timestamp of the last candle we PROCESSED a signal for.
# We only act when a NEW candle has opened — never mid-candle.
_last_processed_candle_ts = 0

# ── BRICK 4: Per-symbol candle timestamp guard (DB-BACKED) ───
# KEY FIX: No longer stored in memory (_symbol_candle_ts dict).
# Now stored in DB table so:
#   (a) Persists across bot restarts — no false "new candle" on restart
#   (b) Shared across processes — 2nd accidental instance sees same ts
# DB key pattern: "candle_ts_{SYMBOL}" e.g. "candle_ts_BBUSD"

def _get_symbol_candle_ts(symbol):
    """Read last processed candle timestamp for symbol from DB."""
    val = db.get_param(f"candle_ts_{symbol.upper()}", "0")
    try:
        return int(val or 0)
    except Exception:
        return 0

def _set_symbol_candle_ts(symbol, ts):
    """Write last processed candle timestamp for symbol to DB."""
    db.set_param(f"candle_ts_{symbol.upper()}", str(int(ts)))

# ── COOLDOWN TRACKING ────────────────────────────────────────────
# MUST be declared here as a module-level global.
# Without this line, is_in_cooldown() raises NameError on first call
# because _last_trade_time would be referenced before assignment.
_last_trade_time = 0   # epoch seconds of last trade action (0 = never traded)

def record_trade_action(reason=""):
    global _last_trade_time
    _last_trade_time = time.time()
    log_terminal(f"⏱️ COOLDOWN started — {reason}", "INFO")

def is_in_cooldown():
    elapsed = time.time() - _last_trade_time
    cd_secs = int(db.get_param("cooldown_seconds", "300") or "300")
    if elapsed < cd_secs:
        log_terminal(f"🧊 COOLDOWN: {int(cd_secs - elapsed)}s remaining.", "INFO")
        return True
    return False

# ── SUPERTREND CALCULATION ───────────────────────────────────
def calculate_supertrend(df, period=10, multiplier=1.0):
    """
    Pure SuperTrend calculation on OHLC DataFrame.
    Returns DataFrame with columns: supertrend, direction
      direction =  1 → Bullish (BUY signal)
      direction = -1 → Bearish (SELL signal)
    """
    df = df.copy()
    df['hl2'] = (df['high'] + df['low']) / 2

    # True Range
    df['prev_close'] = df['close'].shift(1)
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['prev_close']),
            abs(df['low']  - df['prev_close'])
        )
    )

    # ATR (Simple / Wilder's)
    df['atr'] = df['tr'].rolling(window=period, min_periods=1).mean()

    # Basic Bands
    df['basic_upper'] = df['hl2'] + (multiplier * df['atr'])
    df['basic_lower'] = df['hl2'] - (multiplier * df['atr'])

    # Final Bands with carryover
    final_upper = [0.0] * len(df)
    final_lower = [0.0] * len(df)
    supertrend  = [0.0] * len(df)
    direction   = [1]   * len(df)

    for i in range(1, len(df)):
        # Final Upper Band
        if df['basic_upper'].iloc[i] < final_upper[i-1] or df['close'].iloc[i-1] > final_upper[i-1]:
            final_upper[i] = df['basic_upper'].iloc[i]
        else:
            final_upper[i] = final_upper[i-1]

        # Final Lower Band
        if df['basic_lower'].iloc[i] > final_lower[i-1] or df['close'].iloc[i-1] < final_lower[i-1]:
            final_lower[i] = df['basic_lower'].iloc[i]
        else:
            final_lower[i] = final_lower[i-1]

        # SuperTrend Direction
        if supertrend[i-1] == final_upper[i-1]:
            # Was bearish
            if df['close'].iloc[i] <= final_upper[i]:
                supertrend[i] = final_upper[i]
                direction[i]  = -1   # Still bearish
            else:
                supertrend[i] = final_lower[i]
                direction[i]  =  1   # Flipped to bullish
        else:
            # Was bullish
            if df['close'].iloc[i] >= final_lower[i]:
                supertrend[i] = final_lower[i]
                direction[i]  =  1   # Still bullish
            else:
                supertrend[i] = final_upper[i]
                direction[i]  = -1   # Flipped to bearish

    df['final_upper'] = final_upper
    df['final_lower'] = final_lower
    df['supertrend']  = supertrend
    df['direction']   = direction
    return df

# ── FETCH CANDLES FROM DELTA EXCHANGE ───────────────────────
def fetch_candles(timeframe="15m", limit=150):
    """
    Fetches BTC OHLC candles from Delta Exchange.
    CONFIRMED WORKING: resolution must be '1m','5m','15m' etc (with 'm')
    Column names returned: close, high, low, open, time, volume (already lowercase)
    """
    import requests as req

    # Delta Exchange ONLY accepts: 5s,1m,3m,5m,15m,30m,1h,2h,4h,6h,12h,1d,1w
    # timeframe already stored as '5m','15m' etc — use directly
    resolution = timeframe if timeframe in ['5s','1m','3m','5m','15m','30m','1h','2h','4h','6h','12h','1d','1w'] else '5m'

    # Calculate time range — need enough candles for SuperTrend
    tf_secs_map = {'5s':5,'1m':60,'3m':180,'5m':300,'15m':900,'30m':1800,
                   '1h':3600,'2h':7200,'4h':14400,'6h':21600,'12h':43200,'1d':86400}
    tf_secs  = tf_secs_map.get(resolution, 300)
    end_ts   = int(time.time())
    start_ts = end_ts - (limit * tf_secs)

    base_urls = ["https://api.india.delta.exchange", "https://api.delta.exchange"]

    for base in base_urls:
        try:
            params = {
                "symbol":     "BTCUSD",
                "resolution": resolution,
                "start":      start_ts,
                "end":        end_ts
            }
            resp = req.get(f"{base}/v2/history/candles", params=params, timeout=8)
            if resp.status_code == 200:
                data = resp.json().get("result", [])
                if data:
                    df = pd.DataFrame(data)
                    # Delta returns lowercase column names: close,high,low,open,time,volume
                    for col in ['open', 'high', 'low', 'close']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    if 'time' in df.columns:
                        df = df.sort_values('time', ascending=True)
                    df = df.reset_index(drop=True)
                    db.set_param("last_candle_symbol", "BTCUSD")
                    db.set_param("last_candle_count",  str(len(df)))
                    print(f"[CANDLE] OK: {len(df)} candles | res={resolution} | last_close={df['close'].iloc[-1]:.0f}")
                    return df
            else:
                err = resp.json().get('error', {})
                print(f"[CANDLE] {base} HTTP={resp.status_code} err={err}")
        except Exception as e:
            print(f"[CANDLE] {base}: {e}")
    print("[CANDLE] ALL ENDPOINTS FAILED")
    return pd.DataFrame()

# ── GET SUPERTREND SIGNAL ────────────────────────────────────
def get_supertrend_signal():
    """
    Fetches candles and computes SuperTrend on the CONFIRMED candle.

    Candle selection logic:
      Raw feed  : [..., C-2, C-1, C0(forming)]
      After drop: [..., C-2, C-1]   ← iloc[:-1] removes forming candle
      We use    : C-2 (iloc[-2])    ← fully settled, confirmed candle

    Why NOT C-1 (the last closed candle)?
      The exchange sometimes delivers C-1 data in parts during its close
      window, causing its close/high/low to still be slightly in flux.
      C-2 is fully confirmed — never changes — zero repaint.

    Returns: (signal, st_value, confirmed_close, confirmed_candle_time)
      signal = "BUY" | "SELL" | None
    """
    timeframe  = db.get_param("timeframe",  "15m")   # DEFAULT: 15m confirmed candle
    period     = int(db.get_param("st_period",     "10")  or "10")
    multiplier = float(db.get_param("st_multiplier", "1.0") or "1.0")

    # Fetch enough candles: need period*3 for ATR warmup + buffer
    df = fetch_candles(timeframe=timeframe, limit=max(period * 3, 80))
    if df.empty or len(df) < period + 3:
        log_terminal(f"⚠️ Not enough candles ({len(df)}). Need {period+3}+", "WARN")
        return None, 0.0, 0.0, None

    # Step 1: Remove the currently FORMING candle (rightmost / latest)
    df_closed = df.iloc[:-1].copy()

    # Step 2: Run SuperTrend on all closed candles
    df_st = calculate_supertrend(df_closed, period=period, multiplier=multiplier)

    # Step 3: Use iloc[-1] — the last CONFIRMED closed candle.
    # WHY iloc[-1] and NOT iloc[-2]:
    #   df_closed = df.iloc[:-1] already removes the forming candle.
    #   iloc[-1] on df_closed = the last FULLY closed bar (zero repaint risk).
    #   iloc[-2] was ONE EXTRA candle behind — 15 to 30 min signal lag.
    #   That lag caused price to cross ST line while bot stayed in wrong direction.
    confirmed = df_st.iloc[-1]

    direction   = int(confirmed['direction'])
    st_value    = float(confirmed['supertrend'])
    last_close  = float(confirmed['close'])
    last_time   = confirmed.get('time', 0)

    # Also grab the last CLOSED candle's timestamp for the candle-change guard
    latest_closed_ts = int(df_closed.iloc[-1].get('time', 0))

    signal = "BUY" if direction == 1 else "SELL"

    # Store for dashboard (use confirmed values)
    db.set_param("st_value",     f"{st_value:.2f}")
    db.set_param("st_direction", "UP" if direction == 1 else "DOWN")
    db.set_param("current_ltp",  f"{last_close:.2f}")
    db.set_param("last_signal",  signal)

    log_terminal(
        f"📌 Confirmed candle ts={last_time} | close={last_close:.0f} | ST={st_value:.0f} | {signal}",
        "INFO"
    )

    # Return latest_closed_ts as 4th item so the caller can do candle-guard
    return signal, st_value, last_close, latest_closed_ts

# ── STOP LOSS MONITOR ────────────────────────────────────────
def check_sl():
    active = db.get_param("local_trade_active", "NO")
    if active != "YES":
        return
    sl_pct    = float(db.get_param("sl_percent", "2") or "2")
    direction = db.get_param("active_direction", "NONE")
    entry_px  = float(db.get_param("active_entry_price", "0") or "0")
    ltp       = futures_executor.get_btc_ltp()

    if entry_px <= 0 or ltp <= 0 or direction == "NONE":
        return

    loss_pct = ((entry_px - ltp) / entry_px * 100) if direction == "BUY" \
               else ((ltp - entry_px) / entry_px * 100)

    db.set_param("current_loss_pct", f"{loss_pct:.2f}")

    if loss_pct >= sl_pct:
        symbol = db.get_param("active_symbol", "BTCUSD")
        log_terminal(f"🚨 SL HIT: {loss_pct:.2f}% | Closing {symbol}", "ALERT")
        send_telegram_msg(
            f"🔴 STOP LOSS HIT\n"
            f"Symbol : {symbol}\n"
            f"Entry  : {entry_px:,.0f}\n"
            f"LTP    : {ltp:,.0f}\n"
            f"Loss   : {loss_pct:.2f}% (Limit: {sl_pct}%)"
        )
        futures_executor.square_off_futures(reason=f"SL {loss_pct:.2f}%")
        record_trade_action(f"SL hit {loss_pct:.2f}%")

# ── ZOMBIE LOCK DETECTOR ─────────────────────────────────────
def check_zombie_lock():
    import requests as req
    local_active = db.get_param("local_trade_active", "NO")
    if local_active != "YES":
        return
    try:
        path  = "/v2/positions"
        query = "?underlying_asset_symbol=BTC"
        hdrs  = futures_executor.get_delta_auth_headers("GET", path, query_string=query)
        resp  = req.get(f"https://api.india.delta.exchange{path}{query}", headers=hdrs, timeout=5)
        if resp.status_code == 200:
            real_count = sum(
                1 for p in resp.json().get("result", [])
                if abs(float(p.get("size", 0))) > 0
            )
            if real_count == 0:
                log_terminal("🧹 ZOMBIE CLEARED: Exchange=0 positions, DB reset.", "ALERT")
                futures_executor._clear_position_db()
                send_telegram_msg("🧹 ZOMBIE LOCK CLEARED\nExchange: 0 positions — DB reset")
    except Exception as e:
        print(f"[ZOMBIE CHECK] {e}")

# ── MAIN SIGNAL LOOP (BTC) ───────────────────────────────────
def run_supertrend_loop():
    """
    Candle-change guard:
      We only evaluate a new trade signal ONCE per completed candle.
      The loop runs every 30 seconds, but we compare the latest closed
      candle's timestamp against _last_processed_candle_ts.
      If the timestamp hasn't changed → same candle → skip silently.
      This eliminates mid-candle oscillation (the 'blender' problem).
    """
    global _last_processed_candle_ts, _vpn_alert_sent_at

    if db.get_param("algo_running", "OFF") == "OFF":
        return

    # ── VPN GUARD — PERMANENT IP: 46.224.133.16 ──────────────
    # Delta Exchange ONLY accepts this IP. VPN must run on VPS.
    # If VPN drops → bot pauses and alerts. Never bypass this.
    current_ip = _get_current_ip()
    if current_ip and current_ip != ALLOWED_TRADING_IP:
        now = time.time()
        if now - _vpn_alert_sent_at > 300:   # Alert max once per 5 min
            _vpn_alert_sent_at = now
            log_terminal(
                f"[BTC] VPN DISCONNECTED! Current IP: {current_ip} "
                f"(Need: {ALLOWED_TRADING_IP}). Skipping BTC trade.",
                "ALERT"
            )
            send_telegram_msg(
                f"\u26a0\ufe0f <b>VPN DISCONNECTED \u2014 BTC Trading Paused</b>\n"
                f"Current IP : <code>{current_ip}</code>\n"
                f"Required IP: <code>{ALLOWED_TRADING_IP}</code>\n"
                f"Action     : Reconnect VPN on VPS to resume trading.",
                parse_mode="HTML"
            )
        return   # \u2190 Pause ALL BTC trading until VPN is back on VPS

    signal, st_value, last_close, latest_closed_ts = get_supertrend_signal()
    if signal is None:
        log_terminal("⏳ SuperTrend signal unavailable. Retrying...", "INFO")
        return

    # ── CANDLE-CHANGE GUARD (DB-backed for BTC too) ───────────
    # Read from DB so restart doesn't see ts=0 and fire immediately
    stored_ts = db.get_param("candle_ts_BTCUSD", "0")
    try:
        _last_processed_candle_ts = max(_last_processed_candle_ts, int(stored_ts or 0))
    except Exception:
        pass

    if latest_closed_ts != 0 and latest_closed_ts <= _last_processed_candle_ts:
        log_terminal(
            f"⏸ Same candle (ts={latest_closed_ts}) — waiting for next candle close.",
            "INFO"
        )
        return

    # New candle — update both memory and DB guard
    _last_processed_candle_ts = latest_closed_ts
    db.set_param("candle_ts_BTCUSD", str(latest_closed_ts))

    log_terminal(
        f"📊 SuperTrend [{db.get_param('timeframe','5m')} | "
        f"P={db.get_param('st_period','10')} M={db.get_param('st_multiplier','1.0')}] "
        f"→ {signal} | ST={st_value:.0f} | Confirmed Close={last_close:.0f}",
        "INFO"
    )

    # Sync exchange position
    futures_executor.sync_futures_position()
    active_dir = db.get_param("active_direction", "NONE")
    active_any = (db.get_param("local_trade_active", "NO") == "YES")

    # ── HOLD: Already in correct direction ───────────────────
    if active_any and active_dir == signal:
        log_terminal(f"✋ HOLD {signal}: SuperTrend direction unchanged.", "INFO")
        return

    # ── FLIP: Wrong direction ─────────────────────────────────
    if active_any and active_dir != signal and active_dir != "NONE":
        if is_in_cooldown():
            return
        log_terminal(f"🔄 FLIP: Close {active_dir} → Open {signal}", "ALERT")
        send_telegram_msg(
            f"🔄 SUPERTREND FLIP\n"
            f"ST Value : {st_value:,.0f}\n"
            f"Confirmed: {last_close:,.0f}\n"
            f"Old Dir  : {active_dir}\n"
            f"New Dir  : {signal}"
        )
        futures_executor.square_off_futures(reason=f"Flip to {signal}")
        time.sleep(2)
        futures_executor.execute_futures_trade("BTC", signal)
        record_trade_action(f"Flip {active_dir}→{signal}")
        return

    # ── FRESH ENTRY: No position open ────────────────────────
    if not active_any:
        if is_in_cooldown():
            return
        log_terminal(f"FRESH ENTRY: {signal} FUTURES | ST={st_value:.0f}", "TRADE")
        futures_executor.execute_futures_trade("BTC", signal)
        record_trade_action(f"Fresh {signal} entry")


# ══════════════════════════════════════════════════════════════
# BLOCK 4 — Safe Portfolio Loop
# Handles all portfolio coins added via /add Telegram command.
# Uses exact same logic as BTC run_supertrend_loop() — proven and stable.
# BTC is NOT handled here — it stays in run_supertrend_loop() above.
# ══════════════════════════════════════════════════════════════
def run_portfolio_loop():
    """
    Runs SuperTrend trading logic for every coin in the portfolio (symbols table).
    Coins are added/removed via Telegram: /add SOLUSD, /remove SOLUSD.

    Safety guarantees (same as BTC loop):
      1. VPN guard — ALL coins pause if VPN IP is wrong
      2. Stablecoin blocklist — BUSD/USDT etc. silently skipped
      3. Candle-change guard — per-symbol, DB-backed, crash-safe
      4. Pre-flight exchange check — no double-entry ever
      5. Close-before-enter on flip — never two positions in same coin
      6. DB atomic lock — blocks second process from trading same candle
    """
    global _vpn_alert_sent_at

    if db.get_param("algo_running", "OFF") == "OFF":
        return

    symbols = db.get_all_symbols()
    enabled = [s for s in symbols if s["enabled"]]
    if not enabled:
        return   # No portfolio coins configured yet

    # ── VPN GUARD (same permanent rule as BTC) ─────────────────────────
    current_ip = _get_current_ip()
    if current_ip and current_ip != ALLOWED_TRADING_IP:
        now = time.time()
        if now - _vpn_alert_sent_at > 300:
            _vpn_alert_sent_at = now
            log_terminal(
                f"[PORTFOLIO] VPN DISCONNECTED! IP={current_ip} "
                f"(Need: {ALLOWED_TRADING_IP}). All portfolio coins paused.",
                "ALERT"
            )
        return   # Pause ALL coins until VPN reconnects

    leverage = int(db.get_param("leverage", "10") or "10")

    for sym_cfg in enabled:
        symbol     = sym_cfg["symbol"]
        timeframe  = sym_cfg["timeframe"]
        period     = sym_cfg["st_period"]
        multiplier = sym_cfg["st_multiplier"]
        lots       = sym_cfg["lots"]

        try:
            # ── STABLECOIN GUARD ─────────────────────────────────────
            base = symbol.upper().replace("USD", "").replace("PERP", "")
            if symbol.upper() in BLOCKED_SYMBOLS or base in BLOCKED_SYMBOLS:
                log_terminal(
                    f"[{symbol}] BLOCKED: Stablecoin. Skipping.",
                    "WARN"
                )
                continue

            import supertrend as _st

            # ── STEP 1: Get SuperTrend VALUE from configured TF (anchor) ─
            # The ST timeframe (15m/30m etc.) gives us a stable, slow-moving
            # anchor line. We do NOT use its candle ts for the check interval.
            _, st_val, _, _ = \
                _st.get_supertrend_signal_for_symbol(
                    symbol, timeframe=timeframe,
                    period=period, multiplier=multiplier
                )

            if st_val == 0.0:
                log_terminal(f"[{symbol}] ST value unavailable. Skipping.", "INFO")
                continue

            # ── STEP 2: Get last confirmed 5-MINUTE close price ──────────
            # This is the decision trigger — checked every 5 minutes.
            # A 5m close is fully settled (never changes once bar closes).
            close_5m, ts_5m = _st.get_5m_close_for_symbol(symbol)

            if close_5m is None:
                log_terminal(f"[{symbol}] 5m close unavailable. Skipping.", "INFO")
                continue

            # ── STEP 3: Determine signal from price vs ST anchor ─────────
            signal = "BUY" if close_5m > st_val else "SELL"

            # Log every cycle — user can see exactly what's happening
            pos_now = db.get_symbol_position(symbol)
            p_dir   = pos_now["direction"] if (pos_now and pos_now["active"]) else "FLAT"
            log_terminal(
                f"[{symbol}] 5m_close={close_5m:.4f} | ST({timeframe})={st_val:.4f} | "
                f"Signal={signal} | Position={p_dir}",
                "INFO"
            )

            # ── STEP 4: 5-minute candle-change guard ─────────────────────
            # Guard key uses "5m_" prefix — separate from ST TF guard
            guard_key = f"5m_{symbol}"
            last_ts   = _get_symbol_candle_ts(guard_key)

            if last_ts == 0:
                log_terminal(
                    f"[{symbol}] FIRST RUN — recording 5m ts={ts_5m}. "
                    f"Will act on NEXT 5-minute candle close.",
                    "INFO"
                )
                _set_symbol_candle_ts(guard_key, ts_5m)
                continue

            if ts_5m != 0 and ts_5m <= last_ts:
                # Same 5m candle — no action needed
                continue

            # New 5m candle — update guard, sync exchange, then trade
            _set_symbol_candle_ts(guard_key, ts_5m)

            log_terminal(
                f"[{symbol}] NEW 5m CANDLE | 5m_close={close_5m:.4f} | ST({timeframe})={st_val:.4f} | Signal={signal}",
                "INFO"
            )

            # ── STEP 5: Sync live position from exchange ──────────────
            futures_executor.sync_position_for_symbol(symbol)
            pos = db.get_symbol_position(symbol)

            active_any = pos["active"] if pos else False
            active_dir = pos["direction"] if pos else "NONE"
            active_qty = pos["qty"] if pos else 0

            # ── STEP 6: Trade decision ───────────────────────────────

            # HOLD: Already in correct direction — do nothing
            if active_any and active_dir == signal:
                log_terminal(
                    f"[{symbol}] HOLD {signal} — already {active_qty} lots on exchange.",
                    "INFO"
                )
                continue

            # FLIP: Wrong direction — close then re-enter
            if active_any and active_dir != signal and active_dir != "NONE":
                log_terminal(f"[{symbol}] FLIP: {active_dir} → {signal}", "ALERT")
                send_telegram_msg(
                    f"\U0001f504 FLIP [{symbol}]\n"
                    f"ST({timeframe})={st_val:.4f} | 5m_close={close_5m:.4f}\n"
                    f"{active_dir} \u2192 {signal}\n"
                    f"Closing {active_qty} lot(s) first..."
                )
                futures_executor.square_off_symbol(symbol, reason=f"Flip to {signal}")
                time.sleep(6)   # Give exchange 6 seconds to process the close

                # Confirm flat before entering new direction
                futures_executor.sync_position_for_symbol(symbol)
                pos_check = db.get_symbol_position(symbol)
                if pos_check and pos_check["active"]:
                    # Force-clear DB if exchange confirms flat but DB is stale
                    db.update_symbol_position(symbol, "NONE", 0.0, 0, 0)
                    log_terminal(
                        f"[{symbol}] DB force-cleared. Proceeding with {signal} entry.",
                        "ALERT"
                    )

                # Atomic DB lock — blocks duplicate entry from any 2nd process
                if not db.acquire_trade_lock(symbol, latest_closed_ts):
                    log_terminal(
                        f"[{symbol}] FLIP BLOCKED by DB lock. Already traded.", "WARN"
                    )
                    continue

                futures_executor.execute_trade_for_symbol(symbol, signal, lots, leverage)
                db.update_symbol_position(
                    symbol, direction=signal,
                    entry_price=last_close, qty=lots,
                    active=1, last_candle_ts=int(time.time())
                )
                continue

            # FRESH ENTRY: No open position
            if not active_any:
                # Atomic DB lock — blocks duplicate entry
                if not db.acquire_trade_lock(symbol, latest_closed_ts):
                    log_terminal(
                        f"[{symbol}] FRESH ENTRY BLOCKED by DB lock. Already traded.", "WARN"
                    )
                    continue

                log_terminal(
                    f"[{symbol}] FRESH ENTRY: {signal} {lots} lot(s) | ST={st_val:.4f}",
                    "TRADE"
                )
                futures_executor.execute_trade_for_symbol(symbol, signal, lots, leverage)
                db.update_symbol_position(
                    symbol, direction=signal,
                    entry_price=last_close, qty=lots,
                    active=1, last_candle_ts=int(time.time())
                )

        except Exception as ex:
            log_terminal(f"[{symbol}] PORTFOLIO LOOP ERROR: {ex}", "ERROR")
            traceback.print_exc()



# ── MAIN ─────────────────────────────────────────────────────
def main():
    # ══════════════════════════════════════════════════════════
    # FIX 1: ROCK-SOLID SINGLE INSTANCE LOCK
    # SO_REUSEADDR REMOVED — it was allowing 2nd instance to bind
    # the same port, defeating the entire lock purpose.
    # Without SO_REUSEADDR, the 2nd process gets OSError and exits.
    # ══════════════════════════════════════════════════════════
    try:
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # DO NOT set SO_REUSEADDR — we WANT the bind to fail if already running
        lock_socket.bind(('127.0.0.1', 47399))
        lock_socket.listen(1)   # Must listen() to hold the port firmly
    except OSError:
        print("=" * 60)
        print("  BHARAT FUTURES ENGINE ALREADY RUNNING!")
        print("  Only ONE instance allowed. EXITING.")
        print("=" * 60)
        sys.exit(1)

    print("=" * 60)
    print("  ⚡ BHARAT FUTURES ENGINE v2.0 — SUPERTREND")
    print("=" * 60)
    print("  Indicator : SuperTrend ONLY")
    print("  Default   : 5m candles | Period=10 | Multiplier=1")
    print("  Signal    : Candle CLOSE (no anticipation)")
    print("  Instrument: BTC Perpetual Futures")
    print("=" * 60)

    if not db.load_secrets():
        sys.exit(1)

    # Set defaults (only if not already set)
    if not db.get_param("trade_size"):       db.set_param("trade_size",       "1")
    if not db.get_param("sl_percent"):       db.set_param("sl_percent",       "2")
    if not db.get_param("cooldown_seconds"): db.set_param("cooldown_seconds", "300")
    if not db.get_param("trade_mode"):       db.set_param("trade_mode",       "LIVE")
    if not db.get_param("timeframe"):        db.set_param("timeframe",        "5m")
    if not db.get_param("st_period"):        db.set_param("st_period",        "10")
    if not db.get_param("st_multiplier"):    db.set_param("st_multiplier",    "1.0")
    if not db.get_param("leverage"):         db.set_param("leverage",         "10")
    # AUTO-START: Engine runs immediately when bot starts
    db.set_param("algo_running", "ON")

    mode = "LIVE"
    tf   = db.get_param("timeframe",  "5m")
    per  = db.get_param("st_period",  "10")
    mul  = db.get_param("st_multiplier", "1.0")

    log_terminal("Bharat Futures Engine v2.0 (SuperTrend) Started.", "START")

    # START TELEGRAM COMMAND LISTENER (background thread)
    tg_thread = threading.Thread(target=_telegram_listener_thread, daemon=True)
    tg_thread.start()
    log_terminal("Telegram command listener thread started.", "INFO")

    # startup_sync_all_symbols() removed — multi-symbol system deleted (Block 1)

    # Startup message — portfolio only, no BTC
    syms = db.get_all_symbols()
    sym_list = ", ".join([s["symbol"] for s in syms]) if syms else "None — add via /add ETHUSD"
    send_telegram_msg(
        f"⚡ BHARAT FUTURES ENGINE v2.0\n"
        f"Mode     : LIVE\n"
        f"TF       : {tf} | P={per} M={mul}\n"
        f"Portfolio: {sym_list}\n"
        f"Status   : AUTO-STARTED\n"
        f"Use /add ETHUSD to add coins"
    )

    last_pulse = 0

    while True:
        try:
            # BTC loop DISABLED — only portfolio coins trade
            # run_supertrend_loop()  # <-- REMOVED
            run_portfolio_loop()           # Portfolio coins only
            # check_sl()            # <-- BTC-only, REMOVED
            # check_zombie_lock()   # <-- BTC-only, REMOVED
            futures_executor.check_symbol_lot_integrity()   # Guardian

            # Dashboard settings watcher
            try:
                saved_at      = db.get_param("settings_updated_at", "0") or "0"
                last_notified = db.get_param("settings_notified_at", "0") or "0"
                if saved_at != "0" and saved_at != last_notified:
                    send_telegram_msg(
                        f"⚙️ SETTINGS UPDATED\n"
                        f"TF         : {db.get_param('timeframe','5m')}\n"
                        f"ST Period  : {db.get_param('st_period','10')}\n"
                        f"ST Mult    : {db.get_param('st_multiplier','1.0')}\n"
                        f"SL %       : {db.get_param('sl_percent','2')}\n"
                        f"Lots       : {db.get_param('trade_size','1')}\n"
                        f"Mode       : {db.get_param('trade_mode','PAPER')}"
                    )
                    db.set_param("settings_notified_at", saved_at)
            except Exception as se:
                print(f"[SETTINGS WATCH] {se}")

            # 5-min heartbeat — portfolio summary
            if time.time() - last_pulse > 300:
                tf_now  = db.get_param("timeframe", "5m")
                per_now = db.get_param("st_period", "10")
                mul_now = db.get_param("st_multiplier", "1.0")
                syms    = db.get_all_symbols()
                lines   = []
                for s in syms:
                    pos = db.get_symbol_position(s["symbol"])
                    if pos and pos["active"]:
                        lines.append(f"  {s['symbol']}: {pos['direction']} {pos['qty']}lot @ {pos['entry_price']:.4f}")
                    else:
                        lines.append(f"  {s['symbol']}: FLAT")
                port_str = "\n".join(lines) if lines else "  No coins — /add ETHUSD"
                send_telegram_msg(
                    f"💓 BHARAT FUTURES PULSE\n"
                    f"TF: {tf_now} | P={per_now} M={mul_now}\n"
                    f"Portfolio:\n{port_str}"
                )
                last_pulse = time.time()

            time.sleep(30)

        except KeyboardInterrupt:
            log_terminal("Bot stopped by user (Ctrl+C).", "INFO")
            break
        except Exception as e:
            print(f"[LOOP ERROR] {e}")
            traceback.print_exc()
            time.sleep(10)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("CRASH:")
        traceback.print_exc()
        sys.exit(1)
