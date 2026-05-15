import subprocess, time

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def ssh(cmd, timeout=30):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, timeout=timeout
    )
    out = r.stdout.decode('utf-8', errors='replace').strip()
    if out: print(out[:3000])
    return r.returncode

# Kill everything on port 47300
ssh('fuser -k 47300/tcp 2>/dev/null; sleep 2; echo cleared', timeout=10)

# Run bot for exactly 10 seconds inline
print('=== RUN BOT 10 SECONDS INTERACTIVE ===')
r = subprocess.run(
    [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
     '-ssh', f'{vps_user}@{vps_ip}',
     'cd /root/bharat-futures-engine && PYTHONUNBUFFERED=1 timeout 10 python3 -u main.py 2>&1'],
    capture_output=True, timeout=25
)
out = r.stdout.decode('utf-8', errors='replace')
safe = out.encode('ascii', errors='replace').decode('ascii')
print(safe[:3000] if safe else '(no output)')
