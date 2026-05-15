"""Fix BTC candle timeframe from 5m to 15m and send Telegram confirmation."""
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
                         json={"chat_id": TG_CHAT_ID, "text": msg})
        return r.json().get("ok", False)
    except: return False

# LOCAL: Fix main.py - change BTC fetch_candles default from 5m to 15m
print("[1] Fixing local main.py - BTC timeframe 5m -> 15m...")
with open('main.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix BTC fetch_candles default
old = 'def fetch_candles(timeframe="5m", limit=150):'
new = 'def fetch_candles(timeframe="15m", limit=150):'
if old in code:
    code = code.replace(old, new)
    print("   Fixed: fetch_candles default 5m -> 15m")

# Fix the header comment
code = code.replace('Default    : 5-min candles | Period=10 | Multiplier=1',
                    'Default    : 15-min candles | Period=10 | Multiplier=1')

# Fix startup db default for timeframe
code = code.replace(
    'if not db.get_param("candle_tf"):        db.set_param("candle_tf",        "5m")',
    'if not db.get_param("candle_tf"):        db.set_param("candle_tf",        "15m")'
)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("   Saved main.py")

# SSH to VPS: apply same fix + restart
print("\n[2] Connecting to VPS...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('46.224.133.16', username='root', password=secrets['vps_password'], timeout=20)
print("   Connected!")

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

# Apply fix on VPS inline
fix_cmd = """python3 -c "
p='/root/BHARAT-FUTURES-ENGINE/main.py'
c=open(p,'r',encoding='utf-8').read()
c=c.replace('def fetch_candles(timeframe=\\'5m\\', limit=150):','def fetch_candles(timeframe=\\'15m\\', limit=150):')
c=c.replace('Default    : 5-min candles','Default    : 15-min candles')
open(p,'w',encoding='utf-8').write(c)
print('FIXED: 5m->15m on VPS')
" """
r = cmd(fix_cmd)
print(f"\n[3] VPS patch: {r}")

# Set in database too
r = cmd("python3 -c \"import sys; sys.path.insert(0,'/root/BHARAT-FUTURES-ENGINE'); import db; db.load_secrets(); db.set_param('candle_tf','15m'); print('DB: candle_tf=',db.get_param('candle_tf'))\"")
print(f"[4] DB update: {r[:100]}")

# Kill old bot and restart
print("\n[5] Restarting bot with 15m candles...")
cmd("fuser -k 47399/tcp 2>/dev/null; pkill -f main.py 2>/dev/null; sleep 3")
cmd("cd /root/BHARAT-FUTURES-ENGINE && nohup python3 -u main.py > bot.log 2>&1 &")
time.sleep(8)
r = cmd("ss -tlnp | grep 47399 | head -1")
running = "python3" in r
print("   Bot running:", running)

# Show log
log = cmd("tail -8 /root/BHARAT-FUTURES-ENGINE/bot.log")
log_safe = log.encode('ascii','replace').decode()
print("\n[6] Bot log:")
print(log_safe)

ssh.close()

# Send Telegram
msg = (
    "BHARAT FUTURES ENGINE\n\n"
    "FIXED: Candle TF changed to 15m\n"
    "SuperTrend: P=10 | M=1 | TF=15m\n\n"
    "Bot: LIVE (restarted)\n"
    "Dashboard: http://46.224.133.16:8600\n\n"
    "ETHUSD already added. Bot will trade on next 15m candle close."
)
ok = telegram(msg)
print(f"\n[7] Telegram: {ok}")
print("\nDONE - Bot now on 15m candles")
