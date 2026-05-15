import subprocess, time

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
pscp  = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\pscp.exe'
src   = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def ssh(cmd, timeout=25):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, timeout=timeout
    )
    out = r.stdout.decode('utf-8', errors='replace').strip()
    if out:
        safe = out.encode('ascii', errors='replace').decode('ascii')
        print(safe[:1200])

def upload(f):
    r = subprocess.run(
        [pscp, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         f'{src}\\{f}',
         f'{vps_user}@{vps_ip}:/root/bharat-futures-engine/'],
        capture_output=True, text=True, timeout=20
    )
    print(f'  {f}: {"OK" if r.returncode==0 else "FAIL"}')

# The log is stale — wipe it first, then run
print('=== WIPE OLD LOG ===')
ssh('> /root/bharat-futures-engine/bot.log && echo log_wiped', timeout=10)

print()
print('=== TRY RUNNING INTERACTIVELY ===')
ssh('cd /root/bharat-futures-engine && timeout 5 python3 main.py 2>&1 | head -20', timeout=15)

print()
print('=== UPLOAD + RUN FRESH ===')
upload('main.py')

# Fully clear port and try
ssh('fuser -k 47300/tcp 2>/dev/null; sleep 1; echo port_cleared', timeout=10)

# Run with output redirect
ssh(
    'cd /root/bharat-futures-engine && '
    'setsid python3 main.py > bot.log 2>&1 < /dev/null &',
    timeout=10
)
time.sleep(15)

print()
print('=== NEW BOT LOG ===')
ssh('strings /root/bharat-futures-engine/bot.log 2>/dev/null | head -30', timeout=10)

print()
print('=== ALL PROCESSES ===')
ssh('ps aux | grep main.py | grep -v grep | grep -v BHARAT-ALGO', timeout=10)
