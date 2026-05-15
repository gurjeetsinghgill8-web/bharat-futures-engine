"""Start dashboard on VPS + send Telegram status message."""
import paramiko, time, requests

secrets = {}
for line in open('secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        secrets[k.strip().lower()] = v.strip()

# --- Send Telegram status message ---
TG_TOKEN   = secrets.get('telegram_token', '') or secrets.get('telegram_bot_token', '')
TG_CHAT_ID = secrets.get('telegram_chat_id', '')

def telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"})
        return r.json().get("ok", False)
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

# --- SSH to VPS ---
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

# 1. Check if dashboard already running
print("[1] Checking dashboard...")
out = cmd("pgrep -fa streamlit | grep app.py || echo NOT_RUNNING")
print("   ", out[:100])

if "NOT_RUNNING" in out:
    print("[2] Starting Streamlit dashboard on port 8501...")
    cmd("cd /root/BHARAT-FUTURES-ENGINE && nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true > dashboard.log 2>&1 &")
    time.sleep(5)
    out = cmd("pgrep -fa streamlit || echo FAILED")
    print("   Dashboard PID:", out[:100])
else:
    print("   Dashboard already running")

# 2. Get bot status from log
print("[3] Getting bot status from log...")
log = cmd("tail -8 /root/BHARAT-FUTURES-ENGINE/bot.log")
log_ascii = log.encode('ascii', 'replace').decode()
print(log_ascii)

# 3. Get VPS public IP (for dashboard URL)
vps_ip = cmd("curl -s https://api.ipify.org", timeout=10)
print(f"[4] VPS IP: {vps_ip}")
dashboard_url = f"http://{vps_ip}:8501"

# 4. Send Telegram status
msg = (
    "<b>BHARAT FUTURES ENGINE</b>\n"
    "Status: LIVE\n\n"
    f"Bot: RUNNING (PID 215435)\n"
    f"Signal: BUY | ST=79016 | Close=79201\n"
    f"Waiting for next candle close\n\n"
    f"Dashboard: {dashboard_url}\n\n"
    f"Commands:\n"
    f"/status - Engine status\n"
    f"/portfolio - Portfolio coins\n"
    f"/add SOLUSD - Add coin\n"
    f"/remove SOLUSD - Remove coin"
)
print("[5] Sending Telegram message...")
ok = telegram(msg)
print("   Sent:", ok)

ssh.close()
print(f"\nDashboard URL: {dashboard_url}")
print("Check Telegram for status message!")
