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
    if out: print(out[:2000])

# Kill current bot
print('=== KILL CURRENT BOT (91841) ===')
ssh('kill -9 91841 2>/dev/null; fuser -k 47300/tcp 2>/dev/null; sleep 2; echo killed', timeout=10)

# Start with -u flag (unbuffered) + PYTHONUNBUFFERED
print()
print('=== RESTART BOT UNBUFFERED ===')
ssh(
    'PYTHONUNBUFFERED=1 setsid python3 -u /root/bharat-futures-engine/main.py '
    '> /root/bharat-futures-engine/bot.log 2>&1 < /dev/null &'
    ' && echo STARTED',
    timeout=10
)

time.sleep(25)

print()
print('=== BOT LOG ===')
ssh("""python3 -c "
f=open('/root/bharat-futures-engine/bot.log', errors='replace')
lines = f.readlines()
for l in lines[-40:]:
    print(l.rstrip())
" 2>&1""", timeout=10)

print()
print('=== FILE SIZE ===')
ssh('wc -c /root/bharat-futures-engine/bot.log', timeout=5)

print()
print('=== AVAX POSITION ===')
ssh("""cd /root/bharat-futures-engine && python3 -c "
import db
p = db.get_symbol_position('AVAXUSD')
print('active:', p['active'] if p else None, '| dir:', p['direction'] if p else None)
" 2>&1""", timeout=10)
