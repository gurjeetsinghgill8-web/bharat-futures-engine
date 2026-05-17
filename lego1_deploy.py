"""
Clean restart VPS bot after fix.
"""
import paramiko, time
from scp import SCPClient

secrets = {}
for line in open('secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        secrets[k.strip().lower()] = v.strip()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('46.224.133.16', username='root', password=secrets['vps_password'], timeout=20)
print('[OK] Connected to VPS')

def run(cmd, wait=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Verify the fix is on VPS
print('[1] Verifying fix on VPS:')
out = run('grep -n latest_closed_ts /root/BHARAT-FUTURES-ENGINE/main.py || echo NO_BUG_FOUND')
print('   latest_closed_ts check:', out)
out = run('grep -n "buffer_pct" /root/BHARAT-FUTURES-ENGINE/main.py | head -3')
print('   buffer_pct check:', out)

# Kill ALL main.py processes
print('[2] Killing ALL main.py processes...')
run('pkill -9 -f main.py 2>/dev/null')
run('kill -9 437054 2>/dev/null')
time.sleep(3)

out = run('pgrep -f main.py || echo ALL_DEAD')
print('   Remaining:', out)

# Stop service
print('[3] Stopping service...')
run('systemctl stop bharat_futures_bot.service 2>&1')
time.sleep(2)

# Start service (uses new main.py)
print('[4] Starting fresh via systemd...')
out = run('systemctl start bharat_futures_bot.service 2>&1; echo OK')
print('   Start result:', out)
time.sleep(12)

# Verify
print('[5] Final process check:')
out = run('ps aux | grep main.py | grep -v grep')
lines = [l for l in out.split('\n') if l.strip()]
print('   Count:', len(lines))
for l in lines:
    print('   ->', l[:90])

print('[6] Log tail:')
print('-' * 50)
out = run('tail -25 /root/BHARAT-FUTURES-ENGINE/bot.log', wait=15)
print(out)
print('-' * 50)

ssh.close()
print('\nVPS RESTART DONE')
