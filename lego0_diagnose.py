"""
LEGO Step 0B — Find and disable the systemd service keeping the ghost alive.
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

def run(cmd, wait=10):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

# ── Find what is keeping the ghost alive ─────────────────────
print("\n[1] Finding systemd services for BHARAT-ALGO-TRADING-APP:")
out = run("systemctl list-units --type=service --all | grep -i 'bharat\\|futures\\|algo\\|trading\\|bot'")
print(out if out else "   None found in systemctl")

print("\n[2] All active services with 'main.py':")
out = run("systemctl list-units --type=service --state=active | grep -i 'bharat\\|bot\\|futures\\|algo'")
print(out if out else "   None found")

print("\n[3] Checking /etc/systemd/system for related services:")
out = run("ls /etc/systemd/system/ | grep -i 'bharat\\|bot\\|futures\\|algo\\|trading'")
print(out if out else "   None found")

print("\n[4] Checking crontab for auto-restart:")
out = run("crontab -l 2>/dev/null || echo NO_CRONTAB")
print(out)

print("\n[5] Checking supervisor:")
out = run("supervisorctl status 2>/dev/null || echo NO_SUPERVISOR")
print(out)

print("\n[6] Ghost process parent chain (who is restarting it):")
out = run("ps aux | grep 'BHARAT-ALGO-TRADING' | grep -v grep")
print(out if out else "   Not found currently")

print("\n[7] All service files mentioning main.py or BHARAT-ALGO:")
out = run("grep -rl 'BHARAT-ALGO-TRADING\\|bharat-algo' /etc/systemd/system/ 2>/dev/null")
print(out if out else "   None found")

# Also check for pm2
print("\n[8] Checking pm2:")
out = run("pm2 list 2>/dev/null || echo NO_PM2")
print(out)

ssh.close()
print("\nDiagnosis complete.")
