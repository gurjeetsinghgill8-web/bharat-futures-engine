"""
LEGO #4 — Deploy fixed main.py to VPS and restart bot.
Fix: EDEN wrong-side signal bug (Lego #3 code change).
"""
import paramiko, os, time
from scp import SCPClient

secrets = {}
for line in open('secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        secrets[k.strip().lower()] = v.strip()

LOCAL  = r'c:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE'
REMOTE = '/root/BHARAT-FUTURES-ENGINE'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('157.49.187.4', username='root', password=secrets['vps_password'], timeout=20)
print('[OK] Connected to VPS')

def run(cmd, wait=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out + ('\n[STDERR] ' + err if err else '')

# Step 1: Upload fixed main.py
print('\n[1] Uploading fixed main.py...')
with SCPClient(ssh.get_transport()) as scp:
    scp.put(os.path.join(LOCAL, 'main.py'), REMOTE + '/main.py')
print('    OK: main.py uploaded')

# Step 2: Verify the fix landed
print('\n[2] Verifying fix on VPS...')
out = run('grep -n "st_signal" /root/BHARAT-FUTURES-ENGINE/main.py | head -5')
print('   st_signal check:', out or 'NOT FOUND — upload may have failed!')

# Step 3: Kill any stray main.py processes
print('\n[3] Killing ALL existing main.py processes...')
run('pkill -9 -f main.py 2>/dev/null')
time.sleep(3)
out = run('pgrep -f main.py || echo ALL_DEAD')
print('   Remaining:', out)

# Step 4: Stop service cleanly
print('\n[4] Stopping systemd bot service...')
run('systemctl stop bharat_futures_bot.service 2>&1')
time.sleep(2)

# Step 5: Start fresh
print('\n[5] Starting fresh via systemd...')
out = run('systemctl start bharat_futures_bot.service 2>&1; sleep 2; echo STARTED')
print('   Result:', out)
time.sleep(10)

# Step 6: Verify running
print('\n[6] Process check:')
out = run('ps aux | grep main.py | grep -v grep')
lines = [l for l in out.split('\n') if l.strip()]
print(f'   Running instances: {len(lines)}')
for l in lines:
    print('   ->', l[:90])

# Step 7: Show log tail
print('\n[7] Log tail (last 20 lines):')
print('-' * 50)
out = run('tail -20 /root/BHARAT-FUTURES-ENGINE/bot.log', wait=15)
print(out)
print('-' * 50)

ssh.close()
print('\n✅ LEGO #4 COMPLETE — Fixed main.py deployed + bot restarted')
