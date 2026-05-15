import subprocess, time

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def ssh(cmd, timeout=15):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, timeout=timeout
    )
    out = r.stdout.decode('utf-8', errors='replace').strip()
    if out: print(out[:3000])

print('=== BOT LOG (UTF-8 safe) ===')
ssh('python3 -c "f=open(\'/tmp/bot_fresh.txt\',errors=\'replace\'); [print(l.rstrip()) for l in f.readlines()[-40:]]" 2>/dev/null', timeout=10)
print()
print('=== FILE SIZE ===')
ssh('wc -c /tmp/bot_fresh.txt', timeout=5)
