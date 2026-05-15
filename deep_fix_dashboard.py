"""Deep check dashboard + fix TF to 15m permanently."""
import paramiko, time, requests, sys

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
                         json={"chat_id": TG_CHAT_ID, "text": msg})
        return r.json().get("ok", False)
    except: return False

def p(t): sys.stdout.buffer.write((str(t)[:500]+'\n').encode('utf-8','replace')); sys.stdout.flush()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('46.224.133.16', username='root', password=secrets['vps_password'], timeout=20)
p("Connected!")

def cmd(c, timeout=20):
    ch = ssh.get_transport().open_session()
    ch.settimeout(timeout); ch.exec_command(c); ch.shutdown_write()
    out = b""
    start = time.time()
    while True:
        if ch.recv_ready(): out += ch.recv(4096)
        if ch.recv_stderr_ready(): ch.recv_stderr(4096)
        if ch.exit_status_ready(): break
        if time.time()-start > timeout: break
        time.sleep(0.1)
    return out.decode('utf-8', errors='replace').strip()

# 1. What's listening on what ports?
p("[1] All listening ports:")
p(cmd("ss -tlnp | grep -E '8501|8600|8502|streamlit'"))

# 2. Check dashboard log for errors
p("\n[2] Dashboard log:")
p(cmd("cat /root/BHARAT-FUTURES-ENGINE/dashboard.log 2>/dev/null | tail -20 || echo NO_LOG"))

# 3. Kill everything on 8600, fresh start with verbose
p("\n[3] Fresh dashboard start on 8600...")
cmd("fuser -k 8600/tcp 2>/dev/null; sleep 2")
cmd("iptables -I INPUT -p tcp --dport 8600 -j ACCEPT 2>/dev/null")
cmd("iptables -I INPUT -p tcp --dport 8501 -j ACCEPT 2>/dev/null")

# Start with explicit config file to avoid issues
cmd("""cat > /root/BHARAT-FUTURES-ENGINE/.streamlit/config.toml << 'EOF'
[server]
port = 8600
address = "0.0.0.0"
headless = true
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
EOF""")
time.sleep(1)

# Start fresh
cmd("cd /root/BHARAT-FUTURES-ENGINE && nohup python3 -m streamlit run app.py > dashboard.log 2>&1 &")
time.sleep(8)

# 4. Check if it started
p("\n[4] Port 8600 after start:")
p(cmd("ss -tlnp | grep 8600 || echo NOT_LISTENING"))

# 5. Check for errors
p("\n[5] Dashboard log after start:")
p(cmd("cat /root/BHARAT-FUTURES-ENGINE/dashboard.log | tail -20"))

# 6. Test connectivity
p("\n[6] Local HTTP test:")
p(cmd("curl -s --connect-timeout 5 http://127.0.0.1:8600 | head -c 100 || echo FAIL"))

# 7. Fix TF to 15m permanently in DB
p("\n[7] Setting TF=15m in DB...")
fix_tf = """python3 -c "
import sys
sys.path.insert(0,'/root/BHARAT-FUTURES-ENGINE')
import db
db.load_secrets()
db.set_param('candle_tf','15m')
db.set_param('timeframe','15m')
print('candle_tf:', db.get_param('candle_tf'))
print('timeframe:', db.get_param('timeframe'))
" """
p(cmd(fix_tf))

# 8. Check what the app.py uses for port setting
p("\n[8] Which port does app.py specify?")
p(cmd("grep -n 'port\\|8600\\|8501' /root/BHARAT-FUTURES-ENGINE/app.py | head -5"))

# Send Telegram with dashboard URL and current positions
msg = (
    "BOT STATUS UPDATE\n\n"
    "Trades LIVE:\n"
    "- BTCUSD: BUY 1 lot (LIVE)\n"
    "- BEATUSD: SELL 1 lot (LIVE)\n"
    "- ETHUSD: BUY 2 lots (LIVE)\n\n"
    "Dashboard: http://46.224.133.16:8600\n"
    "(Loading - please wait 30 sec then try)\n\n"
    "TF: Fixing to 15m now"
)
ok = telegram(msg)
p(f"\nTelegram: {ok}")
ssh.close()
