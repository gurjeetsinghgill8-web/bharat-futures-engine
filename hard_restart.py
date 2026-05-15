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
    out = r.stdout.decode('utf-8', errors='replace').strip()
    if out:
        safe = out.encode('ascii', errors='replace').decode('ascii')
        print(safe[:800])
    return r.returncode

def upload(fname):
    r = subprocess.run(
        [pscp, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         f'{src}\\{fname}',
         f'{vps_user}@{vps_ip}:/root/bharat-futures-engine/'],
        capture_output=True, text=True, timeout=20
    )
    print(f'  {fname}: {"OK" if r.returncode==0 else "FAIL"}')

print('=== ALL PYTHON PROCESSES ON VPS ===')
ssh('ps aux | grep python3 | grep -v grep')

print()
print('=== KILLING ALL MAIN.PY PROCESSES ===')
ssh('pkill -9 -f main.py; sleep 1; echo killed_all_main', timeout=15)

# Delete lock file if it exists
ssh('rm -f /tmp/bharat_futures.lock /root/bharat-futures-engine/*.lock 2>/dev/null; echo lock_cleared', timeout=10)

time.sleep(3)

print()
print('=== UPLOADING FIXED main.py ===')
upload('main.py')
upload('supertrend.py')

print()
print('=== STARTING FIXED BOT ===')
ssh(
    'setsid python3 /root/bharat-futures-engine/main.py '
    '> /root/bharat-futures-engine/bot.log 2>&1 < /dev/null &'
    ' && echo BOT_STARTED',
    timeout=12
)

time.sleep(12)

print()
print('=== BOT LOG (fresh start) ===')
ssh('strings /root/bharat-futures-engine/bot.log 2>/dev/null | head -30', timeout=10)

print()
print('=== IS BOT RUNNING? ===')
ssh('ps aux | grep "bharat-futures-engine/main.py" | grep -v grep', timeout=10)
