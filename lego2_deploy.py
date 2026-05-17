"""Deploy app.py to VPS and restart dashboard service."""
import paramiko, os
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
ssh.connect('46.224.133.16', username='root', password=secrets['vps_password'], timeout=20)
print('[OK] Connected')

def run(cmd, wait=12):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Upload app.py
print('[1] Uploading app.py...')
with SCPClient(ssh.get_transport()) as scp:
    scp.put(os.path.join(LOCAL, 'app.py'), REMOTE + '/app.py')
print('    OK: app.py uploaded')

# Restart dashboard service
print('[2] Restarting dashboard service...')
out = run('systemctl restart bharat_futures_dash.service 2>&1; sleep 3; echo DONE')
print('   ', out)

# Also check if dashboard is via bharat_dashboard service
out = run('systemctl is-active bharat_futures_dash.service 2>/dev/null || echo NOT_ACTIVE')
print('   bharat_futures_dash:', out)

out = run('systemctl is-active bharat_dashboard.service 2>/dev/null || echo NOT_ACTIVE')
print('   bharat_dashboard:', out)

# Try to restart whichever dashboard service is active
if 'active' not in out.lower():
    out2 = run('systemctl restart bharat_dashboard.service 2>&1; echo DONE')
    print('   Restarted bharat_dashboard:', out2)

# Show running dashboard processes
print('[3] Dashboard processes:')
out = run('ps aux | grep streamlit | grep -v grep | head -5')
for l in out.split('\n'):
    if l.strip():
        print('   ->', l[:90])

ssh.close()
print('\nLEGO 2 DEPLOYED!')
