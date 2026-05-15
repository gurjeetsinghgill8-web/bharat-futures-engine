import subprocess, time

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
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
    if out: print(out[:2000])

print('=== START BOT WITH NOHUP (proper logging) ===')
# Use nohup + exec to ensure output is captured
ssh(
    'export PYTHONUNBUFFERED=1 && '
    'cd /root/bharat-futures-engine && '
    'nohup python3 -u main.py >> bot.log 2>&1 &'
    ' echo PID=$!',
    timeout=10
)

time.sleep(25)

print()
print('=== BOT LOG ===')
ssh("""python3 -c "
f=open('/root/bharat-futures-engine/bot.log', errors='replace')
lines=f.readlines()
print(f'Total lines: {len(lines)}')
for l in lines[-30:]:
    print(l.rstrip())
" 2>&1""", timeout=10)

print()
print('=== AVAX POSITION ===')
ssh("""cd /root/bharat-futures-engine && python3 -c "
import db
p = db.get_symbol_position('AVAXUSD')
a = db.get_param('algo_running')
print('AVAX:', p['direction'] if p else 'N/A', 'active:', p['active'] if p else 'N/A')
print('engine:', a)
" 2>&1""", timeout=10)

print()
print('=== PROCESS ===')
ssh('ps aux | grep "bharat-futures-engine" | grep -v grep', timeout=10)
