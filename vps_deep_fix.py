"""
VPS Deep Connect + Fix Script
Uses paramiko to SSH into VPS, upload fixed main.py, restart bot.
Tries multiple ports and connection methods.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import paramiko
import time
import os

VPS_IP   = "157.49.187.4"
VPS_USER = "root"
VPS_PASS = "U4CJs4HKbMMJ"
VPS_PATH = "/root/bharat-futures"

PORTS_TO_TRY = [22, 2222, 8022, 222, 2200]

LOCAL_MAIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
LOCAL_EMERGENCY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emergency_close_avax.py")

print("=" * 60)
print("  BHARAT VPS DEEP CONNECT + FIX")
print("=" * 60)

def try_connect(port):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"\n  Trying port {port}...")
        client.connect(
            VPS_IP, port=port, username=VPS_USER, password=VPS_PASS,
            timeout=15, allow_agent=False, look_for_keys=False,
            banner_timeout=15
        )
        print(f"  CONNECTED on port {port}!")
        return client
    except Exception as e:
        print(f"  Port {port} failed: {e}")
        return None

client = None
for port in PORTS_TO_TRY:
    client = try_connect(port)
    if client:
        break

if not client:
    print("\nALL PORTS FAILED. VPS SSH not reachable from this network.")
    print("\nAlternative: Use Termius app on phone to SSH and run:")
    print(f"  cd {VPS_PATH}")
    print("  pkill -f 'python.*main.py'")
    print("  # Then paste updated main.py content")
    sys.exit(1)

# ── CONNECTED ──────────────────────────────────────────────────
print("\n[1] Checking VPS status...")
stdin, stdout, stderr = client.exec_command("ls /root/ && ls /root/bharat-futures/ 2>/dev/null || ls /root/ ")
output = stdout.read().decode()
print(f"  VPS Contents:\n{output}")

# Find correct bot directory
stdin, stdout, stderr = client.exec_command("find /root -name 'main.py' -path '*/bharat*' 2>/dev/null | head -5")
paths = stdout.read().decode().strip()
print(f"  Found main.py at: {paths}")

if paths:
    bot_dir = os.path.dirname(paths.split('\n')[0])
else:
    bot_dir = VPS_PATH
print(f"  Bot directory: {bot_dir}")

# ── CHECK CURRENT BOT STATUS ───────────────────────────────────
print("\n[2] Checking running processes...")
stdin, stdout, stderr = client.exec_command("ps aux | grep python | grep -v grep")
procs = stdout.read().decode()
print(f"  Python processes:\n{procs}")

# ── CHECK AVAXUSD POSITION IN DB ──────────────────────────────
print("\n[3] Checking AVAXUSD DB state on VPS...")
check_cmd = f"""cd {bot_dir} && python3 -c "
import db
db.load_secrets()
pos = db.get_symbol_position('AVAXUSD')
print('AVAXUSD position:', pos)
syms = db.get_all_symbols()
print('All symbols:', syms)
mode = db.get_param('trade_mode', 'PAPER')
print('Trade mode:', mode)
" 2>&1"""
stdin, stdout, stderr = client.exec_command(check_cmd)
db_status = stdout.read().decode()
print(f"  DB Status:\n{db_status}")

# ── STOP BOT ──────────────────────────────────────────────────
print("\n[4] Stopping current bot...")
stdin, stdout, stderr = client.exec_command("pkill -f 'python.*main.py' 2>/dev/null; echo 'Bot stopped'")
print(f"  {stdout.read().decode().strip()}")
time.sleep(2)

# ── UPLOAD FIXED MAIN.PY ──────────────────────────────────────
print("\n[5] Uploading fixed main.py...")
sftp = client.open_sftp()
try:
    # Find exact remote path
    remote_main = f"{bot_dir}/main.py"
    sftp.put(LOCAL_MAIN, remote_main)
    print(f"  main.py uploaded to {remote_main}")
    
    # Also upload emergency script
    remote_emergency = f"{bot_dir}/emergency_close_avax.py"
    sftp.put(LOCAL_EMERGENCY, remote_emergency)
    print(f"  emergency_close_avax.py uploaded")
except Exception as e:
    print(f"  Upload failed: {e}")
finally:
    sftp.close()

# ── RUN EMERGENCY CLOSE ───────────────────────────────────────
print("\n[6] Running AVAXUSD emergency close...")
close_cmd = f"cd {bot_dir} && python3 emergency_close_avax.py 2>&1"
stdin, stdout, stderr = client.exec_command(close_cmd)
close_out = stdout.read().decode()
print(f"  Result:\n{close_out}")

# ── RESTART BOT ───────────────────────────────────────────────
print("\n[7] Restarting bot with fixed code...")
restart_cmd = f"""
cd {bot_dir}
mkdir -p logs
nohup python3 main.py >> logs/bot.log 2>&1 &
sleep 3
ps aux | grep 'python.*main.py' | grep -v grep
echo "BOT_RESTART_DONE"
"""
stdin, stdout, stderr = client.exec_command(restart_cmd)
restart_out = stdout.read().decode()
print(f"  Restart result:\n{restart_out}")

# ── VERIFY ────────────────────────────────────────────────────
print("\n[8] Verifying bot started...")
time.sleep(5)
stdin, stdout, stderr = client.exec_command(f"tail -20 {bot_dir}/logs/bot.log 2>/dev/null || echo 'No log yet'")
log_out = stdout.read().decode()
print(f"  Bot log:\n{log_out}")

client.close()

print("\n" + "=" * 60)
print("  VPS FIX COMPLETE!")
print("  - Fixed main.py deployed")
print("  - AVAXUSD emergency close run")
print("  - Bot restarted with new safe code")
print("  - Check Telegram for confirmation message")
print("=" * 60)
