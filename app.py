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
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;900&display=swap');
* { font-family: 'Outfit', sans-serif !important; }
.stApp { background: #0d1117 !important; }

/* Force ALL text white */
p, span, div, label, h1, h2, h3, h4, li { color: #e6edf3 !important; }

/* Streamlit widget labels */
.stSelectbox label, .stNumberInput label, .stSlider label,
.stTextInput label, .stCheckbox label { color: #c9d1d9 !important; font-weight: 600 !important; }

/* Input boxes */
.stTextInput input, .stNumberInput input {
    background: #161b22 !important; color: #e6edf3 !important;
    border: 1px solid #30363d !important; border-radius: 8px !important;
}
.stSelectbox > div > div {
    background: #1c2128 !important; color: #ffffff !important;
    border: 1px solid #58a6ff !important; border-radius: 8px !important;
}
/* Dropdown open list */
[data-baseweb="select"] {
    background: #1c2128 !important;
}
[data-baseweb="select"] * {
    background: #1c2128 !important;
    color: #ffffff !important;
}
[data-baseweb="popover"] {
    background: #1c2128 !important;
}
[data-baseweb="menu"] {
    background: #1c2128 !important;
}
[data-baseweb="option"] {
    background: #1c2128 !important;
    color: #ffffff !important;
}
[data-baseweb="option"]:hover {
    background: #1f6feb !important;
    color: #ffffff !important;
}
ul[role="listbox"] li {
    background: #1c2128 !important;
    color: #ffffff !important;
}
ul[role="listbox"] li:hover {
    background: #1f6feb !important;
}

/* ── Text inputs ─────────────────────────────────────────── */
.stTextInput > div > div > input {
    background: #1c2128 !important;
    color: #ffffff !important;
    border: 1px solid #58a6ff !important;
    border-radius: 8px !important;
    font-size: 14px !important;
}
.stTextInput label {
    color: #c9d1d9 !important;
    font-weight: 600 !important;
}
/* Number inputs */
.stNumberInput input {
    background: #1c2128 !important;
    color: #ffffff !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
}
.stNumberInput label { color: #c9d1d9 !important; }

/* ── Radio buttons ───────────────────────────────────────── */
.stRadio label {
    color: #e6edf3 !important;
    font-size: 13px !important;
}
.stRadio > div {
    gap: 6px !important;
    flex-wrap: wrap !important;
}
.stRadio [data-testid="stMarkdownContainer"] p {
    color: #e6edf3 !important;
}

/* ── Expander: fix text overlap ──────────────────────────── */
.streamlit-expanderContent {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    padding: 16px !important;
    overflow: visible !important;
}
.streamlit-expanderHeader {
    color: #58a6ff !important;
    font-weight: 700 !important;
    background: #0d1117 !important;
    border-radius: 8px !important;
}
/* Fix icon overlap in expander title */
details summary span[data-testid="stExpanderToggleIcon"] {
    display: none !important;
}
details > summary {
    list-style: none !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    padding: 10px 14px !important;
    cursor: pointer !important;
    overflow: hidden !important;
}
details > summary::before {
    content: '▶' !important;
    font-size: 11px !important;
    color: #58a6ff !important;
    flex-shrink: 0 !important;
    transition: transform 0.2s !important;
}
details[open] > summary::before {
    content: '▼' !important;
}
/* Hide the overlapping arrow_right material icon text */
.streamlit-expanderHeader p {
    font-family: 'Source Sans Pro', sans-serif !important;
    font-size: 14px !important;
    color: #58a6ff !important;
    margin: 0 !important;
    overflow: visible !important;
    white-space: normal !important;
}
/* Fix overlapping labels inside expanders */
.streamlit-expanderContent .stTextInput,
.streamlit-expanderContent .stNumberInput,
.streamlit-expanderContent .stRadio,
.streamlit-expanderContent .stSelectbox {
    margin-bottom: 12px !important;
    clear: both !important;
}
/* Ensure all label text is visible */
label, .stMarkdown p, .stMarkdown span {
    color: #e6edf3 !important;
}
div[data-testid="stHorizontalBlock"] {
    gap: 16px !important;
    align-items: flex-start !important;
}

/* Slider */
.stSlider > div { color: #e6edf3 !important; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #1f6feb, #1158c7) !important;
    color: #ffffff !important; border: none !important;
    border-radius: 8px !important; font-weight: 700 !important;
    padding: 10px !important; width: 100% !important;
    font-size: 14px !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #388bfd, #1f6feb) !important;
    transform: translateY(-1px) !important;
}

/* Success / Warning / Error messages */
.stSuccess { background: #1a4731 !important; color: #56d364 !important; border: 1px solid #2ea043 !important; }
.stWarning { background: #3d2b00 !important; color: #d29922 !important; }
.stError   { background: #3d0f0f !important; color: #f85149 !important; }
.element-container .stAlert p { color: inherit !important; }

/* Expander */
.streamlit-expanderHeader { color: #58a6ff !important; font-weight: 700 !important; }
.streamlit-expanderContent { background: #161b22 !important; border: 1px solid #30363d !important; }

/* Dividers */
hr { border-color: #21262d !important; }

/* Metric cards */
.mcard {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 12px; padding: 18px 16px; text-align: center; margin-bottom: 8px;
}
.mcard .lbl { font-size: 10px; color: #8b949e; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 6px; }
.mcard .val { font-size: 26px; font-weight: 900; }
.mcard .sub { font-size: 11px; color: #8b949e; margin-top: 4px; }

/* ST card */
.stcard-up   { background: #0f2d1f; border: 1px solid #2ea043; border-radius: 12px; padding: 18px; text-align: center; }
.stcard-down { background: #2d0f0f; border: 1px solid #f85149; border-radius: 12px; padding: 18px; text-align: center; }

/* Badges */
.badge { display: inline-block; padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; }
.b-on   { background: #1f6feb; color: #fff; }
.b-off  { background: #b22222; color: #fff; }
.b-live { background: #2ea043; color: #fff; }
.b-paper{ background: #9e6a03; color: #fff; }
.b-buy  { background: #2ea043; color: #fff; }
.b-sell { background: #f85149; color: #fff; }
.b-flat { background: #30363d; color: #c9d1d9; }

/* Section headers */
.shdr {
    font-size: 11px; color: #58a6ff; text-transform: uppercase;
    letter-spacing: 3px; font-weight: 700; margin: 18px 0 8px 0;
    border-left: 3px solid #1f6feb; padding-left: 10px;
}
/* Alert / info boxes */
.abox { background: #3d1414; border: 1px solid #f85149; border-radius: 8px; padding: 12px; color: #ff7b72; font-size: 13px; text-align: center; margin: 8px 0; }
.ibox { background: #0d2437; border: 1px solid #1f6feb; border-radius: 8px; padding: 12px; color: #79c0ff; font-size: 13px; text-align: center; margin: 8px 0; }
.sbox { background: #0f2d1f; border: 1px solid #2ea043; border-radius: 8px; padding: 12px; color: #56d364; font-size: 13px; text-align: center; margin: 8px 0; }

/* Trade table */
.ttbl { width: 100%; border-collapse: collapse; }
.ttbl th { background: #161b22; color: #58a6ff; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; padding: 10px; text-align: left; border-bottom: 1px solid #30363d; }
.ttbl td { color: #c9d1d9; font-size: 12px; padding: 9px 10px; border-bottom: 1px solid #21262d; }
.pp { color: #56d364; font-weight: 700; }
.pn { color: #f85149; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

db.init_db()

# ── HEADER ───────────────────────────────────────────────────
h1, h2 = st.columns([3, 1])
with h1:
    st.markdown("""
    <div style='padding:8px 0 12px 0'>
      <div style='font-size:28px;font-weight:900;color:#58a6ff;letter-spacing:-0.5px;'>
        &#9889; BHARAT NEXUS
      </div>
      <div style='color:#8b949e;font-size:12px;margin-top:2px;letter-spacing:3px;'>
        BTC + MULTI-SYMBOL &middot; SUPERTREND PORTFOLIO ENGINE &middot; v6.0
      </div>
    </div>
    """, unsafe_allow_html=True)
with h2:
    now = datetime.datetime.now()
    st.markdown(f"""
    <div style='text-align:right;padding-top:12px'>
      <div style='color:#58a6ff;font-size:22px;font-weight:700;'>{now.strftime('%H:%M:%S')}</div>
      <div style='color:#8b949e;font-size:12px;'>{now.strftime('%d %b %Y')}</div>
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

# ── METRICS ──────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

def mc(label, val, sub, color="#e6edf3"):
    return f"""<div class='mcard'>
      <div class='lbl'>{label}</div>
      <div class='val' style='color:{color}'>{val}</div>
      <div class='sub'>{sub}</div>
    </div>"""

with c1:
    st.markdown(mc("BTC Price", f"${ltp:,.0f}", "Live Spot", "#e6edf3"), unsafe_allow_html=True)
with c2:
    c = "#0f2d1f" if is_up else "#2d0f0f"
    bc = "#2ea043" if is_up else "#f85149"
    vc = "#56d364" if is_up else "#f85149"
    ar = "▲ BULLISH" if is_up else "▼ BEARISH"
    st.markdown(f"""<div style='background:{c};border:1px solid {bc};border-radius:12px;padding:18px;text-align:center;'>
      <div class='lbl'>SuperTrend</div>
      <div class='val' style='color:{vc}'>{st_val:,.0f}</div>
      <div style='color:{vc};font-size:12px;font-weight:700;margin-top:4px;'>{ar}</div>
    </div>""", unsafe_allow_html=True)
with c3:
    sc = "#56d364" if last_signal=="BUY" else ("#f85149" if last_signal=="SELL" else "#8b949e")
    st.markdown(mc("Signal", last_signal, f"TF:{timeframe} P={st_period} M={st_mult}", sc), unsafe_allow_html=True)
with c4:
    pc = "#56d364" if upnl >= 0 else "#f85149"
    ps = f"{active_dir}:{active_sym}" if trade_active=="YES" else "FLAT"
    st.markdown(mc("Live PnL", f"${upnl:+.2f}", ps, pc), unsafe_allow_html=True)
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
        futures_executor.square_off_futures(reason="Manual Dashboard")
        st.error("Square off executed!")
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
        sl_sel  = st.number_input("Stop Loss %", 0.1, 20.0, sl_pct, 0.1, key="sl",  format="%.1f")

    st.divider()
    st.markdown("<div class='shdr'>⚙️ Trade Settings</div>", unsafe_allow_html=True)

    t1, t2 = st.columns(2)
    with t1:
        _cur_mode = db.get_param("trade_mode", "LIVE")
        _mode_idx = 1 if _cur_mode == "LIVE" else 0
        mode_sel = st.selectbox("Trade Mode", ["PAPER", "LIVE"],
                                index=_mode_idx, key="mode")
        qty_sel  = st.number_input("Trade Size (lots)", 1, 100,
                                   int(db.get_param("trade_size","1") or 1), 1, key="qty")
    with t2:
        lev_opts = [5, 10, 25, 50, 100, 200]
        cur_lev  = int(db.get_param("leverage", "10") or 10)
        lev_idx  = lev_opts.index(cur_lev) if cur_lev in lev_opts else 1
        lev_sel  = st.selectbox("Leverage", lev_opts, index=lev_idx, key="lev",
                                help="5x=Safe | 10x=Default | 25x=Medium | 50x+ = High Risk")
        cd_val   = int(db.get_param("cooldown_seconds","300") or 300)
        cd_sel   = st.slider("Cooldown (sec)", 60, 900, cd_val, 60, key="cd")

    if st.button("💾 SAVE ALL SETTINGS", key="btn_save"):
        db.set_param("timeframe",        tf_sel)
        db.set_param("st_period",        str(per_sel))
        db.set_param("st_multiplier",    str(mul_sel))
        db.set_param("sl_percent",       str(sl_sel))
        db.set_param("trade_mode",       mode_sel)
        db.set_param("trade_size",       str(qty_sel))
        db.set_param("leverage",         str(lev_sel))
        db.set_param("cooldown_seconds", str(cd_sel))
        db.set_param("settings_updated_at", str(int(time.time())))
        st.success(f"✅ Saved! TF={tf_sel} P={per_sel} M={mul_sel} SL={sl_sel}% Lots={qty_sel} Lev={lev_sel}x Mode={mode_sel}")

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
st.markdown("<div class='shdr'>➕ Add / Remove Coins</div>", unsafe_allow_html=True)
with st.expander("➕ Click to Add a Coin to Portfolio", expanded=True):
    st.markdown(
        "<div class='ibox'>Enter any Delta Exchange perpetual symbol (e.g. ETHUSD, SOLUSD, XRPUSD).<br>"
        "Coin will trade using the same SuperTrend settings as BTC.</div>",
        unsafe_allow_html=True
    )
    add_c1, add_c2, add_c3 = st.columns([2, 1, 1])
    with add_c1:
        new_sym = st.text_input(
            "Symbol (e.g. ETHUSD)", value="", key="b5_sym",
            placeholder="ETHUSD"
        ).strip().upper()
    with add_c2:
        new_lots = st.number_input("Lots", min_value=1, max_value=50, value=1, step=1, key="b5_lots")
    with add_c3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("✅ ADD COIN", key="btn_add_sym"):
            STABLES = {"BUSD","USDT","USDC","TUSD","USDP","DAI"}
            if not new_sym:
                st.error("Enter a symbol first!")
            elif new_sym.replace("USD","") in STABLES or new_sym in STABLES:
                st.error(f"⚠️ {new_sym} is a stablecoin — blocked!")
            else:
                tf  = db.get_param("timeframe",    "5m")
                per = int(db.get_param("st_period",    "10") or 10)
                mul = float(db.get_param("st_multiplier","1.0") or 1.0)
                db.add_symbol(new_sym, timeframe=tf, st_period=per,
                              st_multiplier=mul, lots=new_lots, enabled=1)
                send_telegram_msg(
                    f"🟢 SYMBOL ADDED: {new_sym}\n"
                    f"TF={tf} | P={per} | M={mul} | Lots={new_lots}"
                )
                st.success(f"✅ {new_sym} added! Bot will trade on next candle close.")
                st.rerun()

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ── Remove / Square Off ────────────────────────────────────────────
if all_syms:
    with st.expander("🔴 Remove or Square Off a Coin"):
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
