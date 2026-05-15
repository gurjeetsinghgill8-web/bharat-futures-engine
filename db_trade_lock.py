

# ══════════════════════════════════════════════════════════════
# FIX 3: DB-LEVEL ATOMIC TRADE EXECUTION LOCK
# ══════════════════════════════════════════════════════════════
# Uses SQLite's atomic INSERT OR IGNORE on a unique key.
# If two processes try to trade the same symbol at the same time,
# only the FIRST one succeeds — the second gets False and skips.
#
# Lock key format: "exec_lock_{SYMBOL}_{CANDLE_TS}"
# This means: one trade max per symbol per candle. EVER.
# ══════════════════════════════════════════════════════════════

def acquire_trade_lock(symbol, candle_ts):
    """
    Atomically acquire a trade execution lock for (symbol, candle_ts).
    Returns True  → safe to trade (no one else claimed this candle yet).
    Returns False → another process already claimed this candle → SKIP.

    Uses SQLite INSERT OR IGNORE — atomic across all processes sharing DB.
    """
    import time as _t
    lock_key = f"exec_lock_{symbol.upper()}_{int(candle_ts)}"
    conn = sqlite3.connect(DB_NAME, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")   # WAL = multi-process safe
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        (lock_key, str(int(_t.time())))
    )
    acquired = cursor.rowcount > 0   # 1 = inserted (got lock); 0 = already existed
    conn.commit()
    conn.close()
    return acquired


def release_old_trade_locks(max_age_seconds=7200):
    """
    Cleanup old exec_lock_ keys (older than 2 hours) to prevent DB bloat.
    Call this once at startup.
    """
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
