"""Deploy app.py to VPS dashboard."""
import paramiko, os
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
print('[OK] Connected')

def run(cmd, wait=12):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=wait)
    return stdout.read().decode('utf-8', errors='replace').strip()

LOCAL  = r'c:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE'
REMOTE = '/root/BHARAT-FUTURES-ENGINE'

print('[1] Uploading app.py...')
with SCPClient(ssh.get_transport()) as scp:
    scp.put(os.path.join(LOCAL, 'app.py'), REMOTE + '/app.py')
print('    OK')

print('[2] Restarting dashboard...')
out = run('systemctl restart bharat_dashboard.service 2>&1; sleep 4; echo DONE')
print('   ', out)

print('[3] Dashboard status:')
out = run('systemctl is-active bharat_dashboard.service')
print('   Active:', out)

print('[4] Streamlit processes:')
out = run('ps aux | grep streamlit | grep -v grep | wc -l')
print('   Count:', out)

ssh.close()
print('DEPLOY DONE')
