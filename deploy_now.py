import subprocess, sys

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
pscp  = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\pscp.exe'
src   = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE'

vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'

HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def ssh(cmd, timeout=90):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch',
         '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, text=True, timeout=timeout
    )
    out = (r.stdout + r.stderr).strip()
    if out:
        print(out[-800:])
    return r.returncode

def scp_upload():
    files = [
        'main.py', 'app.py', 'db.py', 'utils.py',
        'futures_executor.py', 'supertrend.py',
        'analytics.py', 'requirements.txt', 'secrets.txt'
    ]
    for fname in files:
        r = subprocess.run(
            [pscp, '-pw', vps_pass, '-batch',
             '-hostkey', HOSTKEY,
             f'{src}\\{fname}',
             f'{vps_user}@{vps_ip}:/root/bharat-futures-engine/'],
            capture_output=True, text=True, timeout=30
        )
        status = 'OK' if r.returncode == 0 else f'FAIL({r.returncode})'
        print(f'  {fname:30s} {status}')

print('=' * 50)
print('  BHARAT NEXUS v6.0 -- VPS DEPLOY')
print('  Target: 46.224.133.16:8600')
print('=' * 50)

print()
print('[1/4] Creating folder on VPS...')
ssh('mkdir -p /root/bharat-futures-engine')

print()
print('[2/4] Uploading all files...')
scp_upload()

print()
print('[3/4] Installing packages...')
ssh('pip3 install streamlit requests pandas numpy --quiet 2>&1 | tail -5', timeout=180)

print()
print('[4/4] Killing old processes + starting fresh...')
ssh('pkill -9 -f main.py 2>/dev/null; pkill -9 -f streamlit 2>/dev/null; echo killed', timeout=15)

import time
time.sleep(2)

# Write a start script on the VPS
start_script = (
    'cd /root/bharat-futures-engine && '
    'cat > /tmp/start_nexus.sh << \'EOF\'\n'
    '#!/bin/bash\n'
    'cd /root/bharat-futures-engine\n'
    'nohup python3 main.py > bot.log 2>&1 &\n'
    'sleep 2\n'
    'nohup python3 -m streamlit run app.py --server.port 8600 --server.headless true > dash.log 2>&1 &\n'
    'echo STARTED\n'
    'EOF'
)
ssh(start_script, timeout=15)
ssh('chmod +x /tmp/start_nexus.sh && bash /tmp/start_nexus.sh > /tmp/start.log 2>&1 &', timeout=10)

time.sleep(8)
# Check what is running
ssh('ps aux | grep -E "python3|streamlit" | grep -v grep | head -6', timeout=10)
# Check dashboard log
ssh('tail -5 /root/bharat-futures-engine/dash.log 2>/dev/null || echo no dash log yet', timeout=10)

print()
print('=' * 50)
print('  DEPLOY COMPLETE!')
print('  Dashboard: http://46.224.133.16:8600')
print('=' * 50)
