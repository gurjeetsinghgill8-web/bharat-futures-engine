import os
import sqlite3
from datetime import datetime

DB_NAME = "futures_engine.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings 
                      (key TEXT PRIMARY KEY, value TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS trades 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, 
                       symbol TEXT, direction TEXT, entry_price REAL, 
                       exit_price REAL, status TEXT, pnl REAL, qty INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS daily_stats 
                      (date TEXT PRIMARY KEY, total_pnl REAL, status TEXT)''')

    # ── BRICK 1: Multi-Symbol Tables (DO NOT MODIFY ABOVE) ────
    cursor.execute('''CREATE TABLE IF NOT EXISTS symbols
                      (symbol TEXT PRIMARY KEY,
                       timeframe TEXT DEFAULT '5m',
                       st_period INTEGER DEFAULT 10,
                       st_multiplier REAL DEFAULT 1.0,
                       lots INTEGER DEFAULT 1,
                       enabled INTEGER DEFAULT 1)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS symbol_positions
                      (symbol TEXT PRIMARY KEY,
                       direction TEXT DEFAULT 'NONE',
                       entry_price REAL DEFAULT 0.0,
                       qty INTEGER DEFAULT 0,
                       active INTEGER DEFAULT 0,
                       last_candle_ts INTEGER DEFAULT 0)''')
    # ─────────────────────────────────────────────────────────
    conn.commit()
    conn.close()

def load_secrets():
    """Loads API keys from secrets.txt into DB."""
    secrets_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets.txt")
    if not os.path.exists(secrets_file):
        print("\n" + "!"*60)
        print(f"CRITICAL ERROR: secrets.txt NOT FOUND at {secrets_file}")
        print("Format required:")
        print("  DELTA_API_KEY=your_key")
        print("  DELTA_API_SECRET=your_secret")
        print("  TELEGRAM_TOKEN=your_bot_token")
        print("  TELEGRAM_CHAT_ID=your_chat_id")
        print("!"*60 + "\n")
        return False

    _key_map = {
        'telegram_token': 'telegram_bot_token',
        'delta_api_key':  'delta_api_key',
        'delta_api_secret': 'delta_api_secret',
        'trade_mode':     'trade_mode',
        'telegram_chat_id': 'telegram_chat_id',
    }

    loaded = []
    with open(secrets_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            parts = line.split('=', 1)
            if len(parts) != 2:
                continue
            k = parts[0].strip().lower()
            v = parts[1].strip()
            db_key = _key_map.get(k, k)
            # NEVER override trade_mode from secrets.txt
            # trade_mode is controlled ONLY from dashboard
            if k == 'trade_mode':
                continue
            set_param(db_key, v)
            loaded.append(db_key)

    print(f"[secrets] Loaded {len(loaded)} keys: {loaded}")
    return True

def set_param(key, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_param(key, default=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def log_trade(symbol, direction, entry_price, exit_price, pnl, qty=1, status="CLOSED"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""INSERT INTO trades (timestamp, symbol, direction, entry_price, exit_price, status, pnl, qty) 
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                   (timestamp, symbol, direction, entry_price, exit_price, status, pnl, qty))
    conn.commit()
    conn.close()

def get_stats(days=1):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(pnl) FROM trades WHERE timestamp >= datetime('now', ?)", (f'-{days} days',))
    total_pnl = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT COUNT(*) FROM trades WHERE timestamp >= datetime('now', ?)", (f'-{days} days',))
    count = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0 AND timestamp >= datetime('now', ?)", (f'-{days} days',))
    wins = cursor.fetchone()[0] or 0
    win_rate = (wins / count * 100) if count > 0 else 0.0
    avg_pnl  = (total_pnl / count) if count > 0 else 0.0
    conn.close()
    return total_pnl, count, win_rate, avg_pnl

def get_recent_trades(limit=20):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, symbol, direction, entry_price, exit_price, pnl, status FROM trades ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def hard_reset_db():
    """Nuclear reset — clears all trading state. Called from dashboard."""
    keys_to_reset = [
        "algo_running", "active_symbol", "active_pid", "active_direction",
        "active_entry_price", "active_qty", "local_trade_active",
        "unrealized_pnl", "last_signal", "signal_target",
        "order_pending", "crypto_active_symbol",
    ]
    for k in keys_to_reset:
        set_param(k, "NONE" if "symbol" in k or "direction" in k or "signal" in k else "0")
    set_param("algo_running", "OFF")
    set_param("local_trade_active", "NO")
    set_param("order_pending", "NO")
    set_param("active_symbol", "NONE")
    set_param("active_direction", "NONE")
    print("[HARD RESET] All trading state cleared.")

init_db()


# ══════════════════════════════════════════════════════════════
# BRICK 1 — Multi-Symbol Functions (New additions below)
# Existing functions above are NEVER modified.
# ══════════════════════════════════════════════════════════════

def get_all_symbols():
    """
    Returns list of all symbols from the symbols table.
    Each row is a dict with keys: symbol, timeframe, st_period,
    st_multiplier, lots, enabled.
    If enabled=True (default), returns only active symbols.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT symbol, timeframe, st_period, st_multiplier, lots, enabled "
        "FROM symbols ORDER BY symbol"
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "symbol":        r[0],
            "timeframe":     r[1],
            "st_period":     r[2],
            "st_multiplier": r[3],
            "lots":          r[4],
            "enabled":       bool(r[5]),
        }
        for r in rows
    ]


def add_symbol(symbol, timeframe="5m", st_period=10, st_multiplier=1.0, lots=1, enabled=1):
    """
    Inserts or replaces a symbol in the symbols table.
    Calling this again with same symbol updates its settings.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO symbols "
        "(symbol, timeframe, st_period, st_multiplier, lots, enabled) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (symbol.upper(), timeframe, int(st_period), float(st_multiplier), int(lots), int(enabled))
    )
    conn.commit()
    conn.close()
    print(f"[SYMBOLS] add_symbol: {symbol.upper()} tf={timeframe} p={st_period} m={st_multiplier} lots={lots}")


def remove_symbol(symbol):
    """
    Removes a symbol from the symbols table.
    Also clears its position record from symbol_positions.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM symbols WHERE symbol = ?", (symbol.upper(),))
    cursor.execute("DELETE FROM symbol_positions WHERE symbol = ?", (symbol.upper(),))
    conn.commit()
    conn.close()
    print(f"[SYMBOLS] remove_symbol: {symbol.upper()}")


def update_symbol_position(symbol, direction="NONE", entry_price=0.0,
                           qty=0, active=0, last_candle_ts=0):
    """
    Upserts the current position state for a given symbol.
    Called by the multi-symbol engine loop after each trade action.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO symbol_positions "
        "(symbol, direction, entry_price, qty, active, last_candle_ts) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (symbol.upper(), direction, float(entry_price),
         int(qty), int(active), int(last_candle_ts))
    )
    conn.commit()
    conn.close()


def get_symbol_position(symbol):
    """
    Returns the current position record for a given symbol as a dict.
    Keys: symbol, direction, entry_price, qty, active, last_candle_ts
    Returns None if symbol not found.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT symbol, direction, entry_price, qty, active, last_candle_ts "
        "FROM symbol_positions WHERE symbol = ?",
        (symbol.upper(),)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "symbol":          row[0],
        "direction":       row[1],
        "entry_price":     row[2],
        "qty":             row[3],
        "active":          bool(row[4]),
        "last_candle_ts":  row[5],
    }


# ══════════════════════════════════════════════════════════════
# FIX 3: DB-LEVEL ATOMIC TRADE EXECUTION LOCK
# ══════════════════════════════════════════════════════════════
def acquire_trade_lock(symbol, candle_ts):
    """Returns True if lock acquired (safe to trade), False if already taken."""
    import time as _t
    lock_key = f"exec_lock_{symbol.upper()}_{int(candle_ts)}"
    conn = sqlite3.connect(DB_NAME, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        (lock_key, str(int(_t.time())))
    )
    acquired = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return acquired

def release_old_trade_locks(max_age_seconds=7200):
    """Cleanup old exec_lock_ keys older than 2 hours."""
    import time as _t
    cutoff = int(_t.time()) - max_age_seconds
    conn = sqlite3.connect(DB_NAME, timeout=5)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM settings WHERE key LIKE 'exec_lock_%' AND CAST(value AS INTEGER) < ?",
        (cutoff,)
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        print(f"[DB] Cleaned up {deleted} old trade lock(s).")
