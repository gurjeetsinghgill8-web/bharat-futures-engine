import subprocess

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def sshr(cmd, timeout=20):
    """Return raw UTF-8 output"""
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, timeout=timeout
    )
    return r.stdout.decode('utf-8', errors='replace') + r.stderr.decode('utf-8', errors='replace')

# Run python3 -c "import main" and capture output
out = sshr('cd /root/bharat-futures-engine && python3 -c "import main" 2>&1 | head -30')
safe = out.encode('ascii', errors='replace').decode('ascii')
print('=== IMPORT TEST ===')
print(safe[:3000])

# Check syntax
out2 = sshr('cd /root/bharat-futures-engine && python3 -m py_compile main.py && echo SYNTAX_OK || echo SYNTAX_ERROR 2>&1')
safe2 = out2.encode('ascii', errors='replace').decode('ascii')
print()
print('=== SYNTAX CHECK ===')
print(safe2[:500])

# Run in foreground for 3 secs
out3 = sshr('cd /root/bharat-futures-engine && timeout 3 python3 -u main.py 2>&1')
safe3 = out3.encode('ascii', errors='replace').decode('ascii')
print()
print('=== 3-SECOND RUN ===')
print(safe3[:2000])
