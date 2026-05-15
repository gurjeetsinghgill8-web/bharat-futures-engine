"""Check dashboard accessibility and fix firewall, send Telegram update."""
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
    except Exception as e:
        print(f"TG error: {e}"); return False

# Send immediate message
telegram("Working on dashboard fix right now. Please wait 2 minutes...")
print("Telegram: sent update message")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('46.224.133.16', username='root', password=secrets['vps_password'], timeout=20)
print("SSH: Connected!")

def cmd(c, timeout=20):
    transport = ssh.get_transport()
    ch = transport.open_session()
    ch.settimeout(timeout)
    ch.exec_command(c)
    ch.shutdown_write()
    out = b""; err = b""
    start = time.time()
    while True:
        if ch.recv_ready(): out += ch.recv(4096)
        if ch.recv_stderr_ready(): err += ch.recv_stderr(4096)
        if ch.exit_status_ready(): break
        if time.time()-start > timeout: break
        time.sleep(0.1)
    return out.decode('utf-8', errors='replace').strip()

# 1. What is the REAL public IP of this VPS?
print("\n[1] Getting real public IP...")
real_ip = cmd("curl -s https://api.ipify.org", timeout=10)
print(f"    Real public IP: {real_ip}")

# 2. Check iptables - is port 8501 blocked?
print("\n[2] Checking iptables firewall...")
out = cmd("iptables -L INPUT -n | grep -E '8501|REJECT|DROP' | head -10 || echo NO_BLOCKS")
print("   ", out[:300])

# 3. Check if streamlit is running and on which address
print("\n[3] Streamlit process check...")
out = cmd("pgrep -fa streamlit")
print("   ", out[:200] if out else "NOT RUNNING")

# 4. Kill and restart streamlit bound to 0.0.0.0 explicitly
print("\n[4] Restarting dashboard on ALL interfaces...")
cmd("fuser -k 8501/tcp 2>/dev/null; sleep 1")
cmd("cd /root/BHARAT-FUTURES-ENGINE && nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false > dashboard.log 2>&1 &")
time.sleep(6)

# 5. Verify it's listening on 0.0.0.0 (all interfaces)
print("\n[5] Port 8501 status:")
out = cmd("ss -tlnp | grep 8501 || echo NOT_LISTENING")
print("   ", out[:200])

# 6. Open port 8501 in iptables
print("\n[6] Opening port 8501 in iptables...")
out = cmd("iptables -I INPUT -p tcp --dport 8501 -j ACCEPT && echo PORT_OPENED || echo FAILED")
print("   ", out)

# 7. Test if reachable from inside VPS
print("\n[7] Testing local reachability...")
out = cmd(f"curl -s --connect-timeout 3 http://127.0.0.1:8501 | head -c 100 || echo CANNOT_REACH_LOCALLY")
print("   ", out[:100])

# 8. Send Telegram with working URL
dashboard_url = f"http://{real_ip}:8501"
bot_log = cmd("tail -5 /root/BHARAT-FUTURES-ENGINE/bot.log")
bot_log_safe = bot_log.encode('ascii', 'replace').decode()

msg = (
    f"<b>BHARAT FUTURES ENGINE - LIVE</b>\n\n"
    f"<b>Dashboard:</b> {dashboard_url}\n\n"
    f"<b>Bot Status:</b>\n<code>{bot_log_safe}</code>\n\n"
    f"<b>Commands:</b>\n"
    f"/status - Engine status\n"
    f"/portfolio - View coins\n"
    f"/add ETHUSD - Add ETH\n"
    f"/remove ETHUSD - Remove coin"
)
ok = telegram(msg)
print(f"\n[8] Telegram status sent: {ok}")
print(f"\nDashboard URL: {dashboard_url}")
ssh.close()
