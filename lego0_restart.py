"""
LEGO Step 0 — Kill ghost processes, start single clean bot.
"""
import paramiko
import time

secrets = {}
for line in open('secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        secrets[k.strip().lower()] = v.strip()

VPS_IP   = '46.224.133.16'
VPS_USER = 'root'
VPS_PASS = secrets.get('vps_password', '')
BOT_DIR  = '/root/BHARAT-FUTURES-ENGINE'

print("=" * 55)
print("  LEGO STEP 0 - Ghost Process Kill + Clean Restart")
print("=" * 55)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=20)
print("[OK] Connected to VPS: " + VPS_IP)

def run(cmd, wait=10):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    return out

# ── Step 1: Show all running python/main.py processes ────────
print("\n[1] All main.py processes on VPS:")
out = run("ps aux | grep main.py | grep -v grep")
print(out if out else "   (none)")

# ── Step 2: Kill ONLY the old BHARAT-ALGO-TRADING-APP main.py
#    That is the ghost BTC process causing dual heartbeat
print("\n[2] Killing ghost from BHARAT-ALGO-TRADING-APP...")
out = run("pkill -9 -f 'BHARAT-ALGO-TRADING-APP.*main.py' 2>/dev/null; echo DONE")
print("   Ghost kill:", out)
time.sleep(2)

# ── Step 3: Kill the BHARAT-FUTURES-ENGINE main.py too (for clean restart)
print("\n[3] Killing current BHARAT-FUTURES-ENGINE main.py...")
out = run("pkill -9 -f 'BHARAT-FUTURES-ENGINE.*main.py' 2>/dev/null; echo DONE")
# Also kill by pattern
run("pkill -9 -f 'python3 main.py' 2>/dev/null")
run("pkill -9 -f 'python main.py' 2>/dev/null")
time.sleep(3)

# ── Step 4: Verify all dead ───────────────────────────────────
print("\n[4] Checking for survivors...")
out = run("ps aux | grep main.py | grep -v grep")
if out:
    print("   Still running:")
    for line in out.split('\n'):
        print("   -> " + line[:90])
    # Kill remaining by PID
    pids = run("pgrep -f main.py")
    if pids:
        for pid in pids.strip().split('\n'):
            if pid.strip().isdigit():
                run("kill -9 " + pid.strip() + " 2>/dev/null")
                print("   Force killed PID: " + pid.strip())
    time.sleep(2)
else:
    print("   ALL DEAD - clean state!")

# ── Step 5: Start fresh SINGLE instance ──────────────────────
print("\n[5] Starting single fresh bot instance...")
# Write starter script to avoid SSH session issues
run("echo '#!/bin/bash' > /tmp/startbot.sh")
run("echo 'cd /root/BHARAT-FUTURES-ENGINE' >> /tmp/startbot.sh")
run("echo 'nohup python3 main.py >> bot.log 2>&1 &' >> /tmp/startbot.sh")
run("echo 'echo $!' >> /tmp/startbot.sh")
run("chmod +x /tmp/startbot.sh")
pid = run("bash /tmp/startbot.sh")
print("   Bot started, PID: " + pid)
time.sleep(12)

# ── Step 6: Final verification ────────────────────────────────
print("\n[6] FINAL VERIFICATION:")
out = run("ps aux | grep main.py | grep -v grep")
if out:
    lines = [l for l in out.strip().split('\n') if l.strip()]
    print("   Processes running: " + str(len(lines)))
    for l in lines:
        print("   -> " + l[:90])
    if len(lines) == 1:
        print("\n   SUCCESS: Exactly 1 instance running!")
    else:
        print("\n   WARNING: " + str(len(lines)) + " instances! Check manually.")
else:
    print("   ERROR: Bot not running!")

# ── Step 7: Show log ──────────────────────────────────────────
print("\n[7] Bot startup log:")
print("-" * 55)
out = run("tail -20 " + BOT_DIR + "/bot.log", wait=15)
print(out)
print("-" * 55)

ssh.close()
print("\nLEGO STEP 0 COMPLETE")
