import sys
import requests
import db
from datetime import datetime

# Force UTF-8 output on Windows (fixes emoji UnicodeEncodeError)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def send_telegram_msg(message, parse_mode="HTML"):
    """
    Sends a plain message to Telegram.
    Default parse_mode=HTML so <b>, <code> tags work.
    """
    token   = db.get_param('telegram_bot_token')
    chat_id = db.get_param('telegram_chat_id')
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": parse_mode}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        _safe_print(f"Telegram Error: {e}")


def send_trade_alert(symbol, action, lots, leverage, mode, st_val=None, extra=""):
    """
    Sends a COLOR-CODED trade alert to Telegram.
    BUY  → dark green background emoji + bold header
    SELL → red background emoji + bold header
    """
    if action.upper() == "BUY":
        icon   = "🟢"          # Green circle for BUY
        header = f"🟢 <b>BUY ENTRY — {symbol}</b>"
        badge  = "💚 LONG"
    else:
        icon   = "🔴"          # Red circle for SELL
        header = f"🔴 <b>SELL ENTRY — {symbol}</b>"
        badge  = "❤️ SHORT"

    st_line = f"\nST Value : <code>{st_val:.4f}</code>" if st_val is not None else ""
    extra_line = f"\n{extra}" if extra else ""

    msg = (
        f"{header}\n"
        f"{'─'*28}\n"
        f"Action   : <b>{action.upper()}</b>  {badge}\n"
        f"Lots     : <b>{lots}</b>\n"
        f"Leverage : {leverage}x\n"
        f"Mode     : {mode}"
        f"{st_line}"
        f"{extra_line}"
    )
    send_telegram_msg(msg, parse_mode="HTML")


def send_close_alert(symbol, reason, pnl=None, direction=None):
    """
    Sends a color-coded CLOSE / SQUARE OFF alert.
    """
    if direction and direction.upper() == "BUY":
        icon = "🟢"
    elif direction and direction.upper() == "SELL":
        icon = "🔴"
    else:
        icon = "⬜"

    pnl_line = ""
    if pnl is not None:
        pnl_emoji = "✅" if pnl >= 0 else "🔻"
        pnl_line  = f"\nPnL      : {pnl_emoji} <b>${pnl:+.4f}</b>"

    msg = (
        f"{icon} <b>CLOSED — {symbol}</b>\n"
        f"{'─'*28}\n"
        f"Reason   : {reason}"
        f"{pnl_line}"
    )
    send_telegram_msg(msg, parse_mode="HTML")


def log_terminal(message, typ="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {
        "START":  "[START]",
        "INFO":   "[INFO] ",
        "TRADE":  "[TRADE]",
        "ERROR":  "[ERROR]",
        "ALERT":  "[ALERT]",
        "WARN":   "[WARN] ",
        "DEBUG":  "[DEBUG]",
        "RESET":  "[RESET]",
    }
    prefix = icons.get(typ, "[INFO] ")
    msg = f"[{timestamp}] {prefix} {message}"
    _safe_print(msg)
    if typ in ["TRADE", "ALERT", "ERROR", "RESET"]:
        # Use plain text for log_terminal TG messages (no HTML needed here)
        send_telegram_msg(f"<code>BHARAT FUTURES ENGINE:\n{msg}</code>", parse_mode="HTML")


def _safe_print(text):
    """Print that never crashes on Windows encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode('ascii'))
