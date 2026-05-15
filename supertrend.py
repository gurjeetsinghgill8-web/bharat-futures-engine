"""
BHARAT FUTURES ENGINE — SUPERTREND MODULE
==========================================
BRICK 3: Generalized SuperTrend for ANY symbol.

Rules:
- calculate_supertrend()  → exact copy from main.py (logic unchanged)
- fetch_candles_for_symbol() → like main.py's fetch_candles() but accepts
  any Delta Exchange symbol string (not hardcoded to BTCUSD)
- get_supertrend_signal_for_symbol() → full pipeline for one symbol

main.py is NOT modified. Its own functions remain for BTC backward compat.
This module is used ONLY by the new multi-symbol loop (BRICK 4).
==========================================
"""

import time
import socket
import requests
import pandas as pd
import numpy as np

# Force IPv4 — same as main.py
import requests.packages.urllib3.util.connection as urllib3_cn
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

import db

DELTA_BASES = [
    "https://api.india.delta.exchange",
    "https://api.delta.exchange"
]

VALID_RESOLUTIONS = [
    '5s', '1m', '3m', '5m', '15m', '30m',
    '1h', '2h', '4h', '6h', '12h', '1d', '1w'
]

TF_SECS_MAP = {
    '5s': 5, '1m': 60, '3m': 180, '5m': 300,
    '15m': 900, '30m': 1800, '1h': 3600, '2h': 7200,
    '4h': 14400, '6h': 21600, '12h': 43200, '1d': 86400
}


# ── SUPERTREND CALCULATION ────────────────────────────────────
# Exact copy of calculate_supertrend() from main.py.
# DO NOT change this logic — it is the stable, tested version.
def calculate_supertrend(df, period=10, multiplier=1.0):
    """
    Pure SuperTrend calculation on OHLC DataFrame.
    Returns DataFrame with columns: supertrend, direction
      direction =  1 → Bullish (BUY signal)
      direction = -1 → Bearish (SELL signal)
    """
    df = df.copy()
    df['hl2'] = (df['high'] + df['low']) / 2

    df['prev_close'] = df['close'].shift(1)
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['prev_close']),
            abs(df['low']  - df['prev_close'])
        )
    )

    df['atr'] = df['tr'].rolling(window=period, min_periods=1).mean()

    df['basic_upper'] = df['hl2'] + (multiplier * df['atr'])
    df['basic_lower'] = df['hl2'] - (multiplier * df['atr'])

    final_upper = [0.0] * len(df)
    final_lower = [0.0] * len(df)
    supertrend  = [0.0] * len(df)
    direction   = [1]   * len(df)

    for i in range(1, len(df)):
        if df['basic_upper'].iloc[i] < final_upper[i-1] or df['close'].iloc[i-1] > final_upper[i-1]:
            final_upper[i] = df['basic_upper'].iloc[i]
        else:
            final_upper[i] = final_upper[i-1]

        if df['basic_lower'].iloc[i] > final_lower[i-1] or df['close'].iloc[i-1] < final_lower[i-1]:
            final_lower[i] = df['basic_lower'].iloc[i]
        else:
            final_lower[i] = final_lower[i-1]

        if supertrend[i-1] == final_upper[i-1]:
            if df['close'].iloc[i] <= final_upper[i]:
                supertrend[i] = final_upper[i]
                direction[i]  = -1
            else:
                supertrend[i] = final_lower[i]
                direction[i]  =  1
        else:
            if df['close'].iloc[i] >= final_lower[i]:
                supertrend[i] = final_lower[i]
                direction[i]  =  1
            else:
                supertrend[i] = final_upper[i]
                direction[i]  = -1

    df['final_upper'] = final_upper
    df['final_lower'] = final_lower
    df['supertrend']  = supertrend
    df['direction']   = direction
    return df


# ── FETCH CANDLES FOR ANY SYMBOL ────────────────────────────
def fetch_candles_for_symbol(symbol, timeframe="5m", limit=150):
    """
    Fetches OHLC candles from Delta Exchange for ANY perpetual symbol.
    symbol    : e.g. "ETHUSD", "SOLUSD", "BTCUSD"
    timeframe : e.g. "5m", "15m", "1h"
    limit     : number of candles to fetch
    Returns   : pd.DataFrame with columns [open, high, low, close, time, volume]
                or empty DataFrame on failure.
    """
    resolution = timeframe if timeframe in VALID_RESOLUTIONS else '5m'
    tf_secs    = TF_SECS_MAP.get(resolution, 300)
    end_ts     = int(time.time())
    start_ts   = end_ts - (limit * tf_secs)

    for base in DELTA_BASES:
        try:
            params = {
                "symbol":     symbol.upper(),
                "resolution": resolution,
                "start":      start_ts,
                "end":        end_ts
            }
            resp = requests.get(
                f"{base}/v2/history/candles",
                params=params,
                timeout=8
            )
            if resp.status_code == 200:
                data = resp.json().get("result", [])
                if data:
                    df = pd.DataFrame(data)
                    for col in ['open', 'high', 'low', 'close']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    if 'time' in df.columns:
                        df = df.sort_values('time', ascending=True)
                    df = df.reset_index(drop=True)
                    print(
                        f"[ST:{symbol}] {len(df)} candles | "
                        f"res={resolution} | last_close={df['close'].iloc[-1]:.4f}"
                    )
                    return df
            else:
                print(f"[ST:{symbol}] {base} HTTP={resp.status_code}")
        except Exception as e:
            print(f"[ST:{symbol}] {base} error: {e}")

    print(f"[ST:{symbol}] ALL ENDPOINTS FAILED")
    return pd.DataFrame()


# ── GET SUPERTREND SIGNAL FOR ANY SYMBOL ────────────────────
def get_supertrend_signal_for_symbol(symbol, timeframe="5m",
                                     period=10, multiplier=1.0):
    """
    Full pipeline: fetch → calculate → return signal for ONE symbol.

    Candle logic (same as main.py — never changes):
      Raw feed  : [..., C-2, C-1, C0(forming)]
      After drop: [..., C-2, C-1]   ← iloc[:-1] removes forming candle
      Confirmed : C-2 (iloc[-2])    ← fully settled, zero repainting

    Returns:
      (signal, st_value, confirmed_close, latest_closed_ts)
      signal = "BUY" | "SELL" | None on error
    """
    limit = max(period * 3, 80)
    df    = fetch_candles_for_symbol(symbol, timeframe=timeframe, limit=limit)

    if df.empty or len(df) < period + 3:
        print(f"[ST:{symbol}] Not enough candles ({len(df)}). Need {period+3}+")
        return None, 0.0, 0.0, 0

    # Step 1: Drop the forming (rightmost) candle
    # Raw feed : [..., C-2, C-1, C0(forming)]
    # After drop: [..., C-2, C-1]   ← iloc[:-1] removes forming candle
    df_closed = df.iloc[:-1].copy()

    # Step 2: Run SuperTrend on all closed candles
    df_st = calculate_supertrend(df_closed, period=period, multiplier=multiplier)

    # Step 3: Use iloc[-1] — the last FULLY CLOSED candle.
    # WHY iloc[-1] and NOT iloc[-2]:
    #   df_closed already has the forming candle removed.
    #   iloc[-1] on df_closed = the last fully closed bar (zero repaint risk).
    #   iloc[-2] was ONE extra candle behind → signal lag of one full TF period.
    #   That lag caused price to cross ST line while bot stayed in wrong direction.
    #   BTC loop in main.py uses iloc[-1] — this must match exactly.
    confirmed = df_st.iloc[-1]

    direction  = int(confirmed['direction'])
    st_value   = float(confirmed['supertrend'])
    last_close = float(confirmed['close'])
    last_time  = confirmed.get('time', 0)

    # Timestamp of the last CLOSED candle (for candle-change guard in BRICK 4)
    latest_closed_ts = int(df_closed.iloc[-1].get('time', 0))

    signal = "BUY" if direction == 1 else "SELL"

    print(
        f"[ST:{symbol}] ts={last_time} | close={last_close:.4f} | "
        f"ST={st_value:.4f} | {signal}"
    )

    return signal, st_value, last_close, latest_closed_ts
