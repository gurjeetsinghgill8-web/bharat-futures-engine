import subprocess, time

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
        capture_output=True, timeout=timeout
    )
    out = (r.stdout + r.stderr).decode('utf-8', errors='replace').strip()
    safe = out.encode('ascii', errors='replace').decode('ascii')
    if safe: print(safe[:1500])
    return r.returncode

def upload(f):
    r = subprocess.run(
        [pscp, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         f'{src}\\{f}',
         f'{vps_user}@{vps_ip}:/root/bharat-futures-engine/'],
        capture_output=True, text=True, timeout=25
    )
    print(f'  {f}: {"OK" if r.returncode==0 else "FAIL"}')

print('=== TEST IMPORTS ===')
ssh('cd /root/bharat-futures-engine && python3 -c "import db; print(chr(79)+chr(75))" 2>&1', timeout=10)
ssh('cd /root/bharat-futures-engine && python3 -c "import futures_executor; print(chr(79)+chr(75))" 2>&1', timeout=10)
ssh('cd /root/bharat-futures-engine && python3 -c "import supertrend; print(chr(79)+chr(75))" 2>&1', timeout=10)
ssh('cd /root/bharat-futures-engine && python3 -c "import main; print(chr(79)+chr(75))" 2>&1', timeout=10)

print()
print('=== PYTHON VERSION ===')
ssh('python3 --version', timeout=10)

print()
print('=== INSTALLED PACKAGES ===')
ssh('python3 -c "import pandas, numpy, requests; print(chr(65)+chr(76)+chr(76)+chr(32)+chr(79)+chr(75))" 2>&1', timeout=10)

print()
print('=== RUN WITH STDERR REDIRECT ===')
ssh('cd /root/bharat-futures-engine && python3 main.py > /tmp/bot_out.txt 2>&1 & sleep 6 && kill %1 2>/dev/null; cat /tmp/bot_out.txt | iconv -f utf8 -t ascii//TRANSLIT 2>/dev/null | head -30', timeout=20)
