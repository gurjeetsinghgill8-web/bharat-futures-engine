"""
BHARAT NEXUS v6.0 — MULTI-SYMBOL SUPERTREND PORTFOLIO ENGINE
"""
import streamlit as st
import datetime, time
import db, futures_executor
import analytics as anl             # BRICK 7 — Delta Exchange fills
from utils import send_telegram_msg

st.set_page_config(page_title="⚡ BHARAT NEXUS v6.0", page_icon="⚡", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

/* ── BASE: Sky blue background, black text everywhere ── */
* { font-family: 'Inter', sans-serif !important; box-sizing: border-box; }
.stApp, .main, .block-container {
    background: #e8f4fd !important;
}

/* ALL text = black by default */
p, span, div, label, h1, h2, h3, h4, h5, li, small, strong, em {
    color: #111111 !important;
}

/* ── Widget labels ── */
.stSelectbox label, .stNumberInput label, .stSlider label,
.stTextInput label, .stCheckbox label, .stRadio label,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p {
    color: #1a1a1a !important;
    font-weight: 700 !important;
    font-size: 13px !important;
}

/* ── Text inputs ── */
.stTextInput > div > div > input,
.stNumberInput input {
    background: #ffffff !important;
    color: #111111 !important;
    border: 1.5px solid #4a90d9 !important;
    border-radius: 8px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput input:focus {
    border-color: #1565c0 !important;
    box-shadow: 0 0 0 2px rgba(21,101,192,0.15) !important;
}

/* ── Selectbox / Dropdown ── */
.stSelectbox > div > div {
    background: #ffffff !important;
    color: #111111 !important;
    border: 1.5px solid #4a90d9 !important;
    border-radius: 8px !important;
}
[data-baseweb="select"] { background: #ffffff !important; }
[data-baseweb="select"] * { background: #ffffff !important; color: #111111 !important; }
[data-baseweb="popover"], [data-baseweb="menu"] { background: #ffffff !important; }
[data-baseweb="option"] { background: #ffffff !important; color: #111111 !important; }
[data-baseweb="option"]:hover { background: #bbdefb !important; color: #111111 !important; }
ul[role="listbox"] li { background: #ffffff !important; color: #111111 !important; }
ul[role="listbox"] li:hover { background: #bbdefb !important; }

/* ── Slider ── */
.stSlider > div { color: #111111 !important; }
.stSlider [data-testid="stTickBar"] { color: #555555 !important; }
.stSlider [data-testid="stSliderThumbValue"] { color: #1565c0 !important; font-weight: 700 !important; }

/* ── Buttons ── */
.stButton > button {
    background: #1565c0 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    padding: 10px 16px !important;
    width: 100% !important;
    font-size: 14px !important;
    letter-spacing: 0.3px !important;
}
.stButton > button:hover {
    background: #0d47a1 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(21,101,192,0.3) !important;
}

/* ── Alert boxes ── */
.stSuccess, [data-testid="stNotification"][kind="success"] {
    background: #e8f5e9 !important; color: #1b5e20 !important;
    border: 1px solid #43a047 !important; border-radius: 8px !important;
}
.stWarning, [data-testid="stNotification"][kind="warning"] {
    background: #fff8e1 !important; color: #e65100 !important;
    border: 1px solid #fb8c00 !important; border-radius: 8px !important;
}
.stError, [data-testid="stNotification"][kind="error"] {
    background: #fce4ec !important; color: #b71c1c !important;
    border: 1px solid #e53935 !important; border-radius: 8px !important;
}
.element-container .stAlert p { color: inherit !important; }

/* ── Dividers ── */
hr { border-color: #b3d4f0 !important; }

/* ── Expanders ── */
.streamlit-expanderContent,
[data-testid="stExpanderDetails"] {
    background: #ffffff !important;
    border: 1.5px solid #4a90d9 !important;
    border-radius: 0 0 10px 10px !important;
    padding: 16px !important;
}
.streamlit-expanderHeader,
details > summary {
    background: #bbdefb !important;
    color: #0d47a1 !important;
    font-weight: 700 !important;
    border: 1.5px solid #4a90d9 !important;
    border-radius: 8px !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
    cursor: pointer !important;
    list-style: none !important;
}
details > summary::before {
    content: 'v ' !important;
    color: #0d47a1 !important;
    font-size: 12px !important;
}
details[open] > summary::before { content: '^ ' !important; }

/* All text in expanders: black */
.streamlit-expanderContent p, .streamlit-expanderContent span,
.streamlit-expanderContent div, .streamlit-expanderContent label,
[data-testid="stExpanderDetails"] p, [data-testid="stExpanderDetails"] span,
[data-testid="stExpanderDetails"] div, [data-testid="stExpanderDetails"] label,
[data-testid="stExpanderDetails"] small {
    color: #111111 !important;
}

/* Inputs inside expanders */
.streamlit-expanderContent .stTextInput > div > div > input,
[data-testid="stExpanderDetails"] .stTextInput > div > div > input,
.streamlit-expanderContent .stNumberInput input,
[data-testid="stExpanderDetails"] .stNumberInput input {
    background: #f0f8ff !important;
    color: #111111 !important;
    border: 1.5px solid #4a90d9 !important;
    border-radius: 8px !important;
}
.streamlit-expanderContent .stSelectbox > div > div,
[data-testid="stExpanderDetails"] .stSelectbox > div > div {
    background: #f0f8ff !important;
    color: #111111 !important;
    border: 1.5px solid #4a90d9 !important;
}

/* ── Metric / data cards ── */
.mcard {
    background: #ffffff;
    border: 1.5px solid #90caf9;
    border-radius: 12px; padding: 18px 16px;
    text-align: center; margin-bottom: 8px;
    box-shadow: 0 2px 8px rgba(21,101,192,0.08);
}
.mcard .lbl { font-size: 10px; color: #546e7a !important; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 6px; }
.mcard .val { font-size: 26px; font-weight: 800; color: #111111 !important; }
.mcard .sub { font-size: 11px; color: #546e7a !important; margin-top: 4px; }

/* ST cards */
.stcard-up   { background: #e8f5e9; border: 1.5px solid #43a047; border-radius: 12px; padding: 18px; text-align: center; }
.stcard-down { background: #fce4ec; border: 1.5px solid #e53935; border-radius: 12px; padding: 18px; text-align: center; }

/* Badges */
.badge { display: inline-block; padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; }
.b-on   { background: #1565c0; color: #fff !important; }
.b-off  { background: #c62828; color: #fff !important; }
.b-live { background: #2e7d32; color: #fff !important; }
.b-paper{ background: #f57f17; color: #fff !important; }
.b-buy  { background: #2e7d32; color: #fff !important; }
.b-sell { background: #c62828; color: #fff !important; }
.b-flat { background: #78909c; color: #fff !important; }

/* Section headers */
.shdr {
    font-size: 11px; color: #0d47a1 !important;
    text-transform: uppercase; letter-spacing: 3px;
    font-weight: 800; margin: 18px 0 8px 0;
    border-left: 3px solid #1565c0; padding-left: 10px;
}

/* Info / Alert / Success boxes */
.abox { background: #fce4ec; border: 1px solid #e53935; border-radius: 8px; padding: 12px; color: #b71c1c !important; font-size: 13px; text-align: center; margin: 8px 0; }
.ibox { background: #e3f2fd; border: 1px solid #4a90d9; border-radius: 8px; padding: 12px; color: #0d47a1 !important; font-size: 13px; text-align: center; margin: 8px 0; }
.sbox { background: #e8f5e9; border: 1px solid #43a047; border-radius: 8px; padding: 12px; color: #1b5e20 !important; font-size: 13px; text-align: center; margin: 8px 0; }

/* Trade table */
.ttbl { width: 100%; border-collapse: collapse; }
.ttbl th { background: #bbdefb; color: #0d47a1 !important; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; padding: 10px; text-align: left; border-bottom: 2px solid #4a90d9; }
.ttbl td { color: #111111 !important; font-size: 12px; padding: 9px 10px; border-bottom: 1px solid #e3f2fd; background: #ffffff; }
.ttbl tr:hover td { background: #e3f2fd !important; }
.pp { color: #1b5e20 !important; font-weight: 700; }
.pn { color: #b71c1c !important; font-weight: 700; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #e8f4fd; }
::-webkit-scrollbar-thumb { background: #90caf9; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


db.init_db()


# ── HEADER ───────────────────────────────────────────────────
h1, h2 = st.columns([3, 1])
with h1:
    st.markdown("""
    <div style='padding:8px 0 12px 0'>
      <div style='font-size:28px;font-weight:900;color:#0d47a1;letter-spacing:-0.5px;'>
        &#9889; BHARAT NEXUS
      </div>
      <div style='color:#546e7a;font-size:12px;margin-top:2px;letter-spacing:3px;'>
        MULTI-SYMBOL PORTFOLIO &middot; SUPERTREND ENGINE &middot; v6.0
      </div>
    </div>
    """, unsafe_allow_html=True)
with h2:
    now = datetime.datetime.now()
    st.markdown(f"""
    <div style='text-align:right;padding-top:12px'>
      <div style='color:#1565c0;font-size:22px;font-weight:700;'>{now.strftime('%H:%M:%S')}</div>
      <div style='color:#546e7a;font-size:12px;'>{now.strftime('%d %b %Y')}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── LIVE DATA ────────────────────────────────────────────────
ltp          = futures_executor.get_btc_ltp()
st_val       = float(db.get_param("st_value",        "0") or "0")
st_dir       = db.get_param("st_direction", "?")
last_signal  = db.get_param("last_signal",  "?")
active_sym   = db.get_param("active_symbol",    "NONE")
active_dir   = db.get_param("active_direction", "NONE")
entry_px     = float(db.get_param("active_entry_price", "0") or "0")
upnl         = float(db.get_param("unrealized_pnl",    "0") or "0")
trade_active = db.get_param("local_trade_active", "NO")
algo_running = db.get_param("algo_running", "OFF")
trade_mode   = db.get_param("trade_mode",   "PAPER")
sl_pct       = float(db.get_param("sl_percent",  "2") or "2")
timeframe    = db.get_param("timeframe",    "5m")
st_period    = db.get_param("st_period",    "10")
st_mult      = db.get_param("st_multiplier","1.0")
loss_pct     = float(db.get_param("current_loss_pct", "0") or "0")
pnl_24h, trades_24h, wr_24h, _ = db.get_stats(1)
is_up        = (st_dir == "UP")

# ── PORTFOLIO METRICS ────────────────────────────────────────
all_syms_top = db.get_all_symbols()
total_coins  = len(all_syms_top)
active_coins = sum(1 for _s in all_syms_top
                   if (lambda p: p and p["active"])(db.get_symbol_position(_s["symbol"])))

c1, c2, c3, c4, c5 = st.columns(5)

def mc(label, val, sub, color="#e6edf3"):
    return f"""<div class='mcard'>
      <div class='lbl'>{label}</div>
      <div class='val' style='color:{color}'>{val}</div>
      <div class='sub'>{sub}</div>
    </div>"""

with c1:
    ac = "#56d364" if active_coins > 0 else "#8b949e"
    st.markdown(mc("Portfolio Coins", str(total_coins), "Total added"), unsafe_allow_html=True)
with c2:
    ac = "#56d364" if active_coins > 0 else "#8b949e"
    st.markdown(mc("Active Trades", str(active_coins), "Live on exchange", ac), unsafe_allow_html=True)
with c3:
    sc = "#56d364" if last_signal=="BUY" else ("#f85149" if last_signal=="SELL" else "#8b949e")
    st.markdown(mc("ST Signal", last_signal, f"TF:{timeframe} P={st_period} M={st_mult}", sc), unsafe_allow_html=True)
with c4:
    pc = "#56d364" if upnl >= 0 else "#f85149"
    st.markdown(mc("Live PnL", f"${upnl:+.2f}", "Unrealized total", pc), unsafe_allow_html=True)
with c5:
    dc = "#56d364" if pnl_24h >= 0 else "#f85149"
    st.markdown(mc("24h PnL", f"${pnl_24h:+.2f}", f"{trades_24h} trades WR:{wr_24h:.0f}%", dc), unsafe_allow_html=True)


st.divider()

# ── STATUS ROW ───────────────────────────────────────────────
s1, s2, s3, s4 = st.columns(4)
with s1:
    bc = "b-on" if algo_running=="ON" else "b-off"
    st.markdown(f"<div style='text-align:center'><span class='badge {bc}'>ENGINE {'ON ▶' if algo_running=='ON' else 'OFF ■'}</span></div>", unsafe_allow_html=True)
with s2:
    bc = "b-live" if trade_mode=="LIVE" else "b-paper"
    st.markdown(f"<div style='text-align:center'><span class='badge {bc}'>{trade_mode}</span></div>", unsafe_allow_html=True)
with s3:
    if trade_active == "YES":
        bc = "b-buy" if active_dir=="BUY" else "b-sell"
        lb = f"{active_dir} FUTURES"
    else:
        bc, lb = "b-flat", "NO POSITION"
    st.markdown(f"<div style='text-align:center'><span class='badge {bc}'>{lb}</span></div>", unsafe_allow_html=True)
with s4:
    sl_c = "#f85149" if loss_pct/sl_pct > 0.75 else ("#d29922" if loss_pct/sl_pct > 0.4 else "#56d364") if sl_pct > 0 else "#56d364"
    st.markdown(f"<div style='text-align:center;color:#8b949e;font-size:13px;'>SL Risk: <span style='color:{sl_c};font-weight:700;'>{loss_pct:.2f}% / {sl_pct}%</span></div>", unsafe_allow_html=True)

st.divider()

left, right = st.columns(2)

# ── LEFT PANEL ───────────────────────────────────────────────
with left:
    st.markdown("<div class='shdr'>🎮 Engine Control</div>", unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1:
        if st.button("▶ START ENGINE", key="btn_start"):
            db.set_param("algo_running", "ON")
            send_telegram_msg("▶ ENGINE STARTED from Dashboard")
            st.success("Engine started!")
            st.rerun()
    with b2:
        if st.button("■ STOP ENGINE", key="btn_stop"):
            db.set_param("algo_running", "OFF")
            send_telegram_msg("■ ENGINE STOPPED from Dashboard")
            st.warning("Engine stopped.")
            st.rerun()

    st.markdown("<div class='shdr'>🚨 Emergency</div>", unsafe_allow_html=True)
    if st.button("🔴 SQUARE OFF ALL POSITIONS", key="btn_sq"):
        # D-1 FIX: Loop all portfolio coins and close each one.
        # Old code called square_off_futures() = BTC-only, did nothing for alts.
        _syms_all = db.get_all_symbols()
        _closed   = []
        _errors   = []
        for _s in _syms_all:
            try:
                _pos = db.get_symbol_position(_s["symbol"])
                if _pos and _pos["active"]:
                    futures_executor.square_off_symbol(
                        _s["symbol"], reason="Manual Dashboard Square Off"
                    )
                    db.update_symbol_position(_s["symbol"], "NONE", 0.0, 0, 0)
                    _closed.append(_s["symbol"])
            except Exception as _e:
                _errors.append(f"{_s['symbol']}:{_e}")
        if _closed:
            send_telegram_msg(
                "SQUARE OFF ALL (Dashboard)\n"
                "Closed: " + ", ".join(_closed)
            )
            st.error("Closed: " + ", ".join(_closed))
        else:
            st.warning("No open positions to close.")
        if _errors:
            st.error("Errors: " + " | ".join(_errors))
        st.rerun()

    st.divider()

    st.markdown("<div class='shdr'>🔄 System Reset</div>", unsafe_allow_html=True)
    st.markdown("<div class='abox'>⚠️ Hard Reset: Bot stuck hone par use karo</div>", unsafe_allow_html=True)
    b3, b4 = st.columns(2)
    with b3:
        if st.button("🔄 HARD RESET DB", key="btn_reset"):
            db.hard_reset_db()
            send_telegram_msg("🔄 HARD RESET executed")
            st.success("Reset done!")
            st.rerun()
    with b4:
        if st.button("🧹 CLEAR POSITION", key="btn_clr"):
            futures_executor._clear_position_db()
            st.success("Position cleared.")
            st.rerun()

    st.divider()

    # ── SECRETS LOADER ───────────────────────────────────────
    st.markdown("<div class='shdr'>🔑 API Keys Setup</div>", unsafe_allow_html=True)
    st.markdown("<div class='ibox'>✅ Secrets.txt se seedha load karo — Safe hai, sirf is computer pe saved hoga</div>", unsafe_allow_html=True)

    if st.button("📂 LOAD FROM secrets.txt", key="btn_secrets"):
        result = db.load_secrets()
        if result:
            tg  = db.get_param("telegram_bot_token", "")
            cid = db.get_param("telegram_chat_id",   "")
            key = db.get_param("delta_api_key",       "")
            loaded_items = []
            if key:  loaded_items.append("Delta API Key ✅")
            if tg:   loaded_items.append("Telegram Token ✅")
            if cid:  loaded_items.append("Chat ID ✅")
            st.success(f"Loaded: {', '.join(loaded_items)}")
            st.rerun()
        else:
            st.error("secrets.txt not found! Please fill it first.")

    st.markdown("<div class='shdr'>📱 Telegram Test</div>", unsafe_allow_html=True)
    if st.button("📱 SEND TEST MESSAGE", key="btn_tg"):
        tok = db.get_param("telegram_bot_token", "")
        cid = db.get_param("telegram_chat_id",   "")
        if not tok or not cid:
            st.error("❌ Telegram keys missing! Click 'LOAD FROM secrets.txt' first.")
        else:
            send_telegram_msg(
                f"✅ BHARAT FUTURES ENGINE - Test\n"
                f"Time   : {datetime.datetime.now().strftime('%H:%M:%S')}\n"
                f"Mode   : {trade_mode}\n"
                f"LTP    : ${ltp:,.0f}\n"
                f"ST     : {st_val:,.0f} ({st_dir})\n"
                f"Signal : {last_signal}\n"
                f"Status : Connected!"
            )
            st.success("✅ Test message sent! Check Telegram.")

# ── RIGHT PANEL ──────────────────────────────────────────────
with right:
    st.markdown("<div class='shdr'>📊 SuperTrend Settings</div>", unsafe_allow_html=True)
    st.markdown("<div class='ibox'>⚡ Signal = Candle CLOSE based | No repainting</div>", unsafe_allow_html=True)

    r1, r2 = st.columns(2)
    with r1:
        tf_opts = ["5m", "15m", "1m", "3m", "1h"]
        tf_sel  = st.selectbox("Candle Timeframe", tf_opts,
                               index=tf_opts.index(timeframe) if timeframe in tf_opts else 0, key="sel_tf")
        per_sel = st.number_input("Period (ATR Length)", 2, 50, int(st_period or 10), 1, key="per")
    with r2:
        mul_sel = st.number_input("Multiplier", 0.1, 10.0, float(st_mult or 1.0), 0.1, key="mul", format="%.1f")
        sl_sel  = st.number_input("Stop Loss %", 0.1, 100.0, sl_pct, 0.1, key="sl",  format="%.1f")

    st.divider()
    st.markdown("<div class='shdr'>⚙️ Trade Settings</div>", unsafe_allow_html=True)

    t1, t2 = st.columns(2)
    with t1:
        _cur_mode = db.get_param("trade_mode", "LIVE")
        _mode_idx = 1 if _cur_mode == "LIVE" else 0
        mode_sel = st.selectbox("Trade Mode", ["PAPER", "LIVE"],
                                index=_mode_idx, key="mode")
    with t2:
        cd_val   = int(db.get_param("cooldown_seconds","300") or 300)
        cd_sel   = st.slider("Cooldown (sec)", 60, 900, cd_val, 60, key="cd")
    st.markdown(
        "<div class='ibox'>Leverage and Lot Size: set per-coin in Add Coin section below.</div>",
        unsafe_allow_html=True
    )

    if st.button("SAVE ALL SETTINGS", key="btn_save"):
        db.set_param("timeframe",        tf_sel)
        db.set_param("st_period",        str(per_sel))
        db.set_param("st_multiplier",    str(mul_sel))
        db.set_param("sl_percent",       str(sl_sel))
        db.set_param("trade_mode",       mode_sel)
        db.set_param("cooldown_seconds", str(cd_sel))
        db.set_param("settings_updated_at", str(int(time.time())))
        # Sync every portfolio coin's stored TF/P/M to match dashboard.
        # Lots and leverage stay unchanged per-coin.
        for _s in db.get_all_symbols():
            db.add_symbol(_s["symbol"], tf_sel, per_sel, mul_sel,
                          _s["lots"], _s["enabled"])
        st.success(f"Saved! TF={tf_sel} P={per_sel} M={mul_sel} SL={sl_sel}% Cooldown={cd_sel}s Mode={mode_sel}")

    st.divider()
    st.markdown("<div class='shdr'>🔑 Manual Key Entry</div>", unsafe_allow_html=True)
    with st.expander("➕ Enter API Keys Manually (Optional)"):
        st.markdown("<div style='color:#8b949e;font-size:12px;margin-bottom:12px;'>Yahan keys dalne ke baad SAVE karo</div>", unsafe_allow_html=True)
        nk = st.text_input("Delta API Key",      value=db.get_param("delta_api_key",""),      type="password", key="k1")
        ns = st.text_input("Delta API Secret",   value=db.get_param("delta_api_secret",""),   type="password", key="k2")
        nt = st.text_input("Telegram Bot Token", value=db.get_param("telegram_bot_token",""), type="password", key="k3")
        nc = st.text_input("Telegram Chat ID",   value=db.get_param("telegram_chat_id",""),   key="k4")
        st.markdown("")
        if st.button("💾 SAVE KEYS", key="btn_keys"):
            db.set_param("delta_api_key",      nk)
            db.set_param("delta_api_secret",   ns)
            db.set_param("telegram_bot_token", nt)
            db.set_param("telegram_chat_id",   nc)
            st.success("Keys saved to database!")

st.divider()

# ── TRADE TABLE ──────────────────────────────────────────────
st.markdown("<div class='shdr'>📋 Recent Trades</div>", unsafe_allow_html=True)
trades = db.get_recent_trades(20)
if trades:
    rows = ""
    for t in trades:
        ts, sym, dirn, ep, xp, pnl_v, status = t
        pc   = "pp" if (pnl_v or 0) >= 0 else "pn"
        arrow = "🟢" if dirn == "BUY" else "🔴"
        rows += f"<tr><td>{ts}</td><td>{sym}</td><td>{arrow} {dirn}</td><td>${float(ep or 0):,.0f}</td><td>${float(xp or 0):,.0f}</td><td class='{pc}'>${float(pnl_v or 0):+.2f}</td><td>{status}</td></tr>"
    st.markdown(f"""<table class='ttbl'><thead><tr>
        <th>Time</th><th>Symbol</th><th>Direction</th>
        <th>Entry</th><th>Exit</th><th>PnL</th><th>Status</th>
    </tr></thead><tbody>{rows}</tbody></table>""", unsafe_allow_html=True)
else:
    st.markdown("<div class='ibox'>No trades yet. Start the engine to begin.</div>", unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════════════════
# BLOCK 5 — Portfolio Coin Manager (Rebuilt)
# All coins share same TF/Period/Multiplier as BTC (from Settings above).
# Add via Telegram: /add SOLUSD | /remove SOLUSD | /portfolio
# ══════════════════════════════════════════════════════════════
st.markdown("<div class='shdr'>💼 PORTFOLIO COINS (Block 5)</div>", unsafe_allow_html=True)
st.markdown("""
<div class='ibox'>
All portfolio coins use the <b>same SuperTrend settings as BTC</b>
(TF / Period / Multiplier from Settings above). Uniform logic = no config confusion.<br>
<b>From Telegram (mobile):</b> &nbsp;
<code>/add SOLUSD</code> &nbsp;
<code>/remove ETHUSD</code> &nbsp;
<code>/portfolio</code>
</div>
""", unsafe_allow_html=True)

BLOCK5_STABLECOINS = {"BUSD","USDT","USDC","TUSD","USDP","DAI"}

# ── Live Portfolio Status Table ───────────────────────────────────────
all_syms = db.get_all_symbols()

if all_syms:
    st.markdown("<div class='shdr'>📍 Live Status</div>", unsafe_allow_html=True)
    port_rows = ""
    for s in all_syms:
        sym  = s["symbol"]
        lots = s["lots"]
        pos  = db.get_symbol_position(sym)
        if pos and pos["active"]:
            dirn    = pos["direction"]
            ep      = pos["entry_price"]
            qty     = pos["qty"]
            d_color = "#56d364" if dirn == "BUY" else "#f85149"
            arrow   = "🟢" if dirn == "BUY" else "🔴"
            pos_str = f"<span style='color:{d_color};font-weight:700'>{arrow} {dirn} x{qty} @ {ep:,.4f}</span>"
            dir_badge = f"<span class='badge b-{'buy' if dirn=='BUY' else 'sell'}'>{'LONG' if dirn=='BUY' else 'SHORT'}</span>"
        else:
            pos_str   = "<span style='color:#8b949e'>― FLAT</span>"
            dir_badge = "<span class='badge b-flat'>FLAT</span>"
        en_badge = "<span class='badge b-on'>ON</span>" if s["enabled"] else "<span class='badge b-off'>OFF</span>"
        port_rows += (
            f"<tr>"
            f"<td style='font-weight:700;color:#58a6ff'>{sym}</td>"
            f"<td>{lots} lot(s)</td>"
            f"<td>{en_badge}</td>"
            f"<td>{dir_badge}</td>"
            f"<td>{pos_str}</td>"
            f"</tr>"
        )
    st.markdown(f"""<table class='ttbl'>
        <thead><tr>
          <th>Symbol</th><th>Lots</th><th>Engine</th>
          <th>Direction</th><th>Position</th>
        </tr></thead>
        <tbody>{port_rows}</tbody>
    </table>""", unsafe_allow_html=True)
    st.markdown("")
else:
    st.markdown(
        "<div class='ibox'>Portfolio is empty.<br>"
        "Add a coin below or send <code>/add SOLUSD</code> in Telegram.</div>",
        unsafe_allow_html=True
    )

# ── Add Coin ────────────────────────────────────────────────────────
st.markdown("<div class='shdr'>ADD / REMOVE COINS</div>", unsafe_allow_html=True)
with st.expander("Click to Add a Coin to Portfolio", expanded=True):
    st.markdown(
        "<div class='ibox'>Enter any Delta Exchange perpetual symbol (e.g. ETHUSD, SOLUSD, XRPUSD).<br>"
        "Coin will trade using the same SuperTrend TF/Period/Multiplier set in Settings above.</div>",
        unsafe_allow_html=True
    )
    add_c1, add_c2, add_c3, add_c4 = st.columns([2, 1, 1, 1])
    with add_c1:
        raw_sym = st.text_input(
            "Symbol (e.g. ETHUSD)", value="", key="b5_sym",
            placeholder="ETHUSD",
            help="Type any symbol — it auto-converts to UPPERCASE"
        )
        new_sym = raw_sym.strip().upper()
        if raw_sym and raw_sym != raw_sym.upper():
            st.caption(f"Will use: {new_sym}")

    with add_c2:
        new_lots = st.number_input("Lots", min_value=1, max_value=500, value=1, step=1, key="b5_lots")
    with add_c3:
        _lev_opts = [5, 10, 25, 50, 100, 200]
        new_lev = st.selectbox("Leverage", _lev_opts, index=1, key="b5_lev",
                               help="Per-coin leverage")
    with add_c4:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("✅ ADD COIN", key="btn_add_sym"):
            STABLES = {"BUSD","USDT","USDC","TUSD","USDP","DAI"}
            if not new_sym:
                st.error("Enter a symbol first!")
            elif new_sym.replace("USD","") in STABLES or new_sym in STABLES:
                st.error(f"{new_sym} is a stablecoin — blocked!")
            else:
                tf  = db.get_param("timeframe",     "15m")
                per = int(db.get_param("st_period",   "10") or 10)
                mul = float(db.get_param("st_multiplier","2.5") or 2.5)
                db.add_symbol(new_sym, timeframe=tf, st_period=per,
                              st_multiplier=mul, lots=new_lots, enabled=1)
                # Save leverage per-coin as a separate param key
                db.set_param(f"leverage_{new_sym}", str(new_lev))
                send_telegram_msg(
                    f"SYMBOL ADDED: {new_sym}\n"
                    f"TF={tf} | P={per} | M={mul} | Lots={new_lots} | Lev={new_lev}x"
                )
                st.success(f"{new_sym} added! Lots={new_lots} Leverage={new_lev}x. Bot trades on next candle close.")
                st.rerun()

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ── Remove / Square Off ────────────────────────────────────────────
if all_syms:
    with st.expander("Remove or Square Off a Coin"):
        sym_names = [s["symbol"] for s in all_syms]
        rem_c1, rem_c2, rem_c3 = st.columns(3)
        with rem_c1:
            rem_sym = st.selectbox("Select Symbol", sym_names, key="rem_sym_sel")
        with rem_c2:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("🗑️ REMOVE", key="btn_rem_sym"):
                db.remove_symbol(rem_sym)
                send_telegram_msg(f"🗑️ SYMBOL REMOVED: {rem_sym}")
                st.warning(f"{rem_sym} removed from portfolio.")
                st.rerun()
        with rem_c3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("⏸ SQUARE OFF", key="btn_sq_sym"):
                futures_executor.square_off_symbol(rem_sym, reason="Manual Dashboard")
                st.error(f"Square off sent for {rem_sym}!")
                st.rerun()


# ── Enable / Disable toggle ──────────────────────────────────────────
if all_syms:
    st.markdown("<div class='shdr'>⚡ Enable / Disable Individual Symbols</div>", unsafe_allow_html=True)
    n_cols = max(1, min(len(all_syms), 5))
    tog_cols = st.columns(n_cols)
    for i, s in enumerate(all_syms):
        with tog_cols[i % n_cols]:
            cur_en  = s["enabled"]
            btn_lbl = f"{'ON' if cur_en else 'OFF'} {s['symbol']}"
            if st.button(btn_lbl, key=f"tog_{s['symbol']}"):
                db.add_symbol(
                    s["symbol"], s["timeframe"], s["st_period"],
                    s["st_multiplier"], s["lots"],
                    0 if cur_en else 1
                )
                st.rerun()


# ══════════════════════════════════════════════════════════════
# BRICK 6 — LIVE PERFORMANCE ANALYTICS
# Added BELOW symbol manager. Zero changes above this line.
# ══════════════════════════════════════════════════════════════
st.divider()
st.markdown("<div class='shdr'>📈 LIVE PERFORMANCE ANALYTICS</div>", unsafe_allow_html=True)

cur_mode = "LIVE"

if cur_mode != "LIVE":
    st.markdown(
        "<div class='abox'>⚠️ PAPER mode active — switch to LIVE to see real "
        "exchange fills. Local DB simulation shown below.</div>",
        unsafe_allow_html=True
    )

# Period selector
p1, p2, _ = st.columns([1, 1, 4])
with p1:
    perf_days = st.selectbox(
        "Period", [1, 7, 30],
        format_func=lambda x: {1: "Today", 7: "7 Days", 30: "30 Days"}[x],
        key="perf_days_sel"
    )
with p2:
    st.button("🔄 Refresh", key="btn_refresh_anl")

# Fetch data
if cur_mode == "LIVE":
    with st.spinner("Fetching from Delta Exchange..."):
        summary = anl.get_performance_summary(days=perf_days)
    data_label = "Delta Exchange (Real)"
else:
    local_pnl, local_cnt, local_wr, _ = db.get_stats(days=perf_days)
    wins   = int(local_cnt * local_wr / 100) if local_cnt else 0
    losses = local_cnt - wins
    summary = {
        "total_trades":    local_cnt,
        "wins":            wins,
        "losses":          losses,
        "win_rate":        round(local_wr, 1),
        "gross_pnl":       round(local_pnl, 2),
        "total_brokerage": 0.0,
        "net_pnl":         round(local_pnl, 2),
        "by_symbol":       {},
        "fill_count":      local_cnt,
        "mode":            "PAPER"
    }
    data_label = "Local DB (Paper Simulation)"

# Metric cards row
a1, a2, a3, a4, a5 = st.columns(5)

def amc(label, val, sub, color="#e6edf3"):
    return f"""<div class='mcard'>
      <div class='lbl'>{label}</div>
      <div class='val' style='color:{color}'>{val}</div>
      <div class='sub'>{sub}</div>
    </div>"""

pnl_c = "#56d364" if summary["net_pnl"] >= 0 else "#f85149"
gr_c  = "#56d364" if summary["gross_pnl"] >= 0 else "#f85149"
wr_c  = "#56d364" if summary["win_rate"] >= 50 else "#d29922"

with a1:
    st.markdown(
        amc("Net PnL", f"${summary['net_pnl']:+.2f}",
            f"After ${summary['total_brokerage']:.4f} fees", pnl_c),
        unsafe_allow_html=True
    )
with a2:
    st.markdown(
        amc("Gross PnL", f"${summary['gross_pnl']:+.2f}",
            f"{summary['total_trades']} total fills", gr_c),
        unsafe_allow_html=True
    )
with a3:
    st.markdown(
        amc("Win Rate", f"{summary['win_rate']}%",
            f"{summary['wins']}W / {summary['losses']}L", wr_c),
        unsafe_allow_html=True
    )
with a4:
    st.markdown(
        amc("Brokerage", f"${summary['total_brokerage']:.4f}",
            "Fees paid to exchange", "#d29922"),
        unsafe_allow_html=True
    )
with a5:
    st.markdown(
        amc("Trades", str(summary["total_trades"]),
            f"Source: {data_label}", "#e6edf3"),
        unsafe_allow_html=True
    )

# Per-symbol breakdown table
if summary.get("by_symbol"):
    st.markdown("<div class='shdr'>📊 Per-Symbol Breakdown</div>", unsafe_allow_html=True)
    sym_rows = ""
    for sym, info in sorted(summary["by_symbol"].items()):
        sym_rows += (
            f"<tr>"
            f"<td style='font-weight:700;color:#58a6ff'>{sym}</td>"
            f"<td>{info['trades']}</td>"
            f"<td style='color:#d29922'>${info['brokerage']:.4f}</td>"
            f"</tr>"
        )
    st.markdown(f"""<table class='ttbl'>
        <thead><tr>
          <th>Symbol</th><th>Fills</th><th>Brokerage Paid</th>
        </tr></thead>
        <tbody>{sym_rows}</tbody>
    </table>""", unsafe_allow_html=True)
else:
    st.markdown(
        f"<div class='ibox'>No fills data for last {perf_days}d. "
        f"In LIVE mode — trades must be executed first.</div>",
        unsafe_allow_html=True
    )

# ── Final Footer ──────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center;color:#30363d;font-size:11px;'>"
    "BHARAT NEXUS v6.0 · BTC + Multi-Symbol · SuperTrend Portfolio Engine · Port 8600"
    "</div>",
    unsafe_allow_html=True
)

# Auto-refresh 30s
st.markdown("<script>setTimeout(()=>window.location.reload(),30000)</script>", unsafe_allow_html=True)
