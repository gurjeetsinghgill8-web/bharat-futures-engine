import subprocess

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
pscp  = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\pscp.exe'
src   = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def ssh(cmd, timeout=20):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, text=True, timeout=timeout
    )
    if r.stdout.strip(): print(r.stdout.strip())
    return r.returncode

def upload(fname):
    r = subprocess.run(
        [pscp, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         f'{src}\\{fname}',
         f'{vps_user}@{vps_ip}:/root/bharat-futures-engine/'],
        capture_output=True, text=True, timeout=20
    )
    print(f'  {fname}: {"OK" if r.returncode==0 else "FAIL"}')

print('=== QUICK UPDATE: app.py only ===')
upload('app.py')

print('Restarting dashboard...')
ssh('fuser -k 8600/tcp; sleep 2', timeout=10)
ssh('setsid python3 -m streamlit run /root/bharat-futures-engine/app.py --server.port 8600 --server.headless true --server.address 0.0.0.0 > /root/bharat-futures-engine/dash.log 2>&1 < /dev/null &', timeout=10)

import time; time.sleep(6)
ssh('ss -tlnp | grep 8600 || echo not_up_yet', timeout=10)
print('Done! http://46.224.133.16:8600')
