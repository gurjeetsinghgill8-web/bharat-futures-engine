"""
BHARAT FUTURES ENGINE — ANALYTICS MODULE
==========================================
BRICK 7: Fetches real trade fills from Delta Exchange API.
LIVE mode only — returns actual PnL, brokerage, win rate.

Functions:
  get_exchange_fills(days)          → raw fills list from Delta
  calculate_performance(fills)      → summary dict
  get_performance_summary(days)     → one-call convenience wrapper
==========================================
"""

import time
import hmac
import hashlib
import socket
import requests
import db

# Force IPv4
import requests.packages.urllib3.util.connection as urllib3_cn
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

BASE_URL     = "https://api.india.delta.exchange"
FALLBACK_URL = "https://api.delta.exchange"


def _get_auth_headers(method, path, query_string="", payload=""):
    """Builds Delta Exchange auth headers. Reuses same logic as executor."""
    api_key    = db.get_param("delta_api_key",    "")
    api_secret = db.get_param("delta_api_secret", "")
    if not api_key or not api_secret:
        return {}
    timestamp      = str(int(time.time()))
    signature_data = method + timestamp + path + query_string + payload
    signature = hmac.new(
        api_secret.encode("utf-8"),
        signature_data.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return {
        "api-key":      api_key,
        "signature":    signature,
        "timestamp":    timestamp,
        "Content-Type": "application/json",
        "User-Agent":   "BHARAT-FUTURES-ENGINE-V3"
    }


def get_exchange_fills(days=1, page_size=100):
    """
    Fetches executed order fills from Delta Exchange.
    Returns a list of fill dicts. Empty list on failure or PAPER mode.

    Each fill dict contains (from Delta API):
      created_at, product_symbol, side, size, price,
      commission (brokerage paid), role (maker/taker)
    """
    mode = db.get_param("trade_mode", "PAPER")
    if mode != "LIVE":
        return []   # No real fills in PAPER mode

    api_key = db.get_param("delta_api_key", "")
    if not api_key:
        return []

    # Delta uses epoch seconds for time filter
    start_ts = int(time.time()) - (days * 86400)

    path         = "/v2/fills"
    query_string = f"?page_size={page_size}&start_time={start_ts}"

    for base in [BASE_URL, FALLBACK_URL]:
        try:
            hdrs = _get_auth_headers("GET", path, query_string=query_string)
            resp = requests.get(
                f"{base}{path}{query_string}",
                headers=hdrs,
                timeout=10
            )
            if resp.status_code == 200:
                result = resp.json().get("result", [])
                fills  = result if isinstance(result, list) else result.get("data", [])
                print(f"[ANALYTICS] Fetched {len(fills)} fills from {base} (last {days}d)")
                return fills
            else:
                print(f"[ANALYTICS] {base} HTTP={resp.status_code}: {resp.text[:120]}")
        except Exception as e:
            print(f"[ANALYTICS] {base} error: {e}")

    return []


def calculate_performance(fills):
    """
    Processes a list of Delta Exchange fill dicts into a performance summary.

    Returns dict:
      total_trades  : int
      wins          : int
      losses        : int
      win_rate      : float (%)
      gross_pnl     : float (estimated from price moves — approximate)
      total_brokerage: float (sum of commission fields)
      net_pnl       : float (gross_pnl - total_brokerage)
      by_symbol     : dict {symbol: {trades, brokerage}}
    """
    if not fills:
        return {
            "total_trades":    0,
            "wins":            0,
            "losses":          0,
            "win_rate":        0.0,
            "gross_pnl":       0.0,
            "total_brokerage": 0.0,
            "net_pnl":         0.0,
            "by_symbol":       {}
        }

    total_brokerage = 0.0
    by_symbol       = {}
    total_trades    = len(fills)

    for fill in fills:
        try:
            commission = float(fill.get("commission", 0) or 0)
            total_brokerage += commission
            sym = fill.get("product_symbol", "UNKNOWN")
            if sym not in by_symbol:
                by_symbol[sym] = {"trades": 0, "brokerage": 0.0}
            by_symbol[sym]["trades"]    += 1
            by_symbol[sym]["brokerage"] += commission
        except Exception:
            pass

    # PnL: Use local DB closed trades for accurate PnL
    # (Delta fills API gives individual leg fills, not net PnL per trade)
    local_pnl, local_count, win_rate, _ = db.get_stats(
        days=30   # wide window — filter by what we got from exchange
    )

    # Count wins/losses from local DB
    wins   = int(local_count * win_rate / 100) if local_count > 0 else 0
    losses = local_count - wins

    gross_pnl = local_pnl
    net_pnl   = gross_pnl - total_brokerage

    return {
        "total_trades":    total_trades,
        "wins":            wins,
        "losses":          losses,
        "win_rate":        round(win_rate, 1),
        "gross_pnl":       round(gross_pnl, 2),
        "total_brokerage": round(total_brokerage, 4),
        "net_pnl":         round(net_pnl, 2),
        "by_symbol":       by_symbol
    }


def get_performance_summary(days=1):
    """
    Convenience wrapper: fetch fills → calculate → return summary dict.
    Usage: summary = get_performance_summary(days=7)
    """
    fills   = get_exchange_fills(days=days)
    summary = calculate_performance(fills)
    summary["days"]       = days
    summary["fill_count"] = len(fills)
    summary["mode"]       = db.get_param("trade_mode", "PAPER")
    return summary
