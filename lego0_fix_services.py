"""
LEGO Step 0C — Stop and disable ghost services, start clean futures bot.
"""
import paramiko
import time

secrets = {}
for line in open('secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        secrets[k.strip().lower()] = v.strip()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('46.224.133.16', username='root', password=secrets['vps_password'], timeout=20)
print("[OK] Connected")

def run(cmd, wait=12):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

# ── Step 1: Read what bharat_engine.service contains ─────────
print("\n[1] Reading bharat_engine.service:")
out = run("cat /etc/systemd/system/bharat_engine.service")
print(out)

print("\n[2] Reading bharat_futures_bot.service:")
out = run("cat /etc/systemd/system/bharat_futures_bot.service 2>/dev/null || echo NOT_FOUND")
print(out)

# ── Step 2: STOP and DISABLE the ghost engine ─────────────────
# bharat_engine.service = BHARAT-ALGO-TRADING-APP engine (OLD ghost)
print("\n[3] Stopping bharat_engine.service (ghost BTC engine)...")
out = run("systemctl stop bharat_engine.service 2>&1 && echo STOPPED || echo FAILED")
print("   ", out)

print("\n[4] Disabling bharat_engine.service (prevent auto-restart)...")
out = run("systemctl disable bharat_engine.service 2>&1 && echo DISABLED || echo FAILED")
print("   ", out)

# Wait for it to die
time.sleep(3)

# ── Step 3: Verify ghost is dead ─────────────────────────────
print("\n[5] Verifying BHARAT-ALGO-TRADING-APP ghost is dead:")
out = run("ps aux | grep 'BHARAT-ALGO-TRADING-APP.*main.py' | grep -v grep")
print(out if out else "   DEAD - ghost killed successfully!")

# ── Step 4: Check bharat_futures_bot.service status ─────────
print("\n[6] bharat_futures_bot.service status:")
out = run("systemctl status bharat_futures_bot.service 2>&1 | head -20")
print(out)

# ── Step 5: Check what is currently running ──────────────────
print("\n[7] All main.py processes now:")
out = run("ps aux | grep main.py | grep -v grep")
print(out if out else "   None running")

# ── Step 6: Start BHARAT-FUTURES-ENGINE properly via service ─
print("\n[8] Starting bharat_futures_bot.service...")
out = run("systemctl start bharat_futures_bot.service 2>&1 && echo STARTED || echo FAILED")
print("   ", out)
time.sleep(10)

print("\n[9] Final process check:")
out = run("ps aux | grep main.py | grep -v grep")
if out:
    lines = [l for l in out.strip().split('\n') if l.strip()]
    print("   Running: " + str(len(lines)) + " process(es)")
    for l in lines:
        print("   -> " + l[:95])
else:
    print("   Nothing running!")

print("\n[10] Bot log tail:")
print("-" * 55)
out = run("tail -20 /root/BHARAT-FUTURES-ENGINE/bot.log", wait=15)
print(out)
print("-" * 55)

ssh.close()
print("\nLEGO STEP 0C COMPLETE")
