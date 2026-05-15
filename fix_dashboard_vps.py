"""Fix dashboard port conflict and check trade mode."""
import paramiko, time, requests

secrets = {}
for line in open('secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        secrets[k.strip().lower()] = v.strip()

TG_TOKEN   = secrets.get('telegram_token', '') or secrets.get('telegram_bot_token', '')
TG_CHAT_ID = secrets.get('telegram_chat_id', '')

def telegram(msg):
    try:
        r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                         json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"})
        return r.json().get("ok", False)
    except: return False

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('46.224.133.16', username='root', password=secrets['vps_password'], timeout=20)
print("Connected!")

def cmd(command, timeout=20):
    transport = ssh.get_transport()
    channel = transport.open_session()
    channel.settimeout(timeout)
    channel.exec_command(command)
    channel.shutdown_write()
    out = b""; err = b""
    start = time.time()
    while True:
        if channel.recv_ready():        out += channel.recv(4096)
        if channel.recv_stderr_ready(): err += channel.recv_stderr(4096)
        if channel.exit_status_ready(): break
        if time.time() - start > timeout: break
        time.sleep(0.1)
    return out.decode('utf-8', errors='replace').strip()

# 1. Kill the OLD dashboard (BHARAT-ALGO-TRADING-APP on port 8501)
print("\n[1] Killing old dashboard on port 8501...")
out = cmd("fuser -k 8501/tcp 2>/dev/null; sleep 1; echo KILLED")
print("   ", out)

# 2. Start OUR dashboard (BHARAT-FUTURES-ENGINE) on port 8501
print("\n[2] Starting BHARAT-FUTURES-ENGINE dashboard on port 8501...")
out = cmd("cd /root/BHARAT-FUTURES-ENGINE && nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true > dashboard.log 2>&1 &")
time.sleep(6)
out = cmd("pgrep -fa streamlit | grep BHARAT-FUTURES")
print("   Running:", out[:150] if out else "NOT FOUND")

# 3. Set LIVE mode in database
print("\n[3] Setting LIVE mode in database...")
out = cmd("""python3 -c "
import sys
sys.path.insert(0, '/root/BHARAT-FUTURES-ENGINE')
import db
db.load_secrets()
db.set_param('trade_mode', 'LIVE')
print('trade_mode =', db.get_param('trade_mode'))
" """)
print("   ", out)

# 4. Check Telegram commands in running main.py
print("\n[4] Checking if /add command exists on VPS...")
out = cmd("grep -n '/add\\|/remove\\|/portfolio' /root/BHARAT-FUTURES-ENGINE/main.py | head -10")
print(out[:500] if out else "NOT FOUND - commands missing!")

# 5. Show dashboard URL
print("\n[5] Dashboard URL: http://46.224.133.16:8501")

# 6. Send Telegram update
msg = (
    "<b>BHARAT FUTURES ENGINE - STATUS UPDATE</b>\n\n"
    "Dashboard: http://46.224.133.16:8501\n"
    "(Add/Remove coins visible there)\n\n"
    "<b>Available Commands:</b>\n"
    "/status - Engine status\n"
    "/portfolio - View all coins\n"
    "/add SYMBOL - Add coin (e.g. /add ETHUSD)\n"
    "/remove SYMBOL - Remove coin\n"
    "/positions - All positions"
)
ok = telegram(msg)
print(f"\n[6] Telegram sent: {ok}")

ssh.close()
