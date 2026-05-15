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
    if out:
        safe = out.encode('ascii', errors='replace').decode('ascii')
        print(safe[:1000])

print('=== WHO IS HOLDING PORT 47300? ===')
ssh('ss -tlnp | grep 47300 || echo port_free', timeout=10)
ssh('fuser 47300/tcp 2>/dev/null || echo no_fuser', timeout=10)
ssh('lsof -i :47300 2>/dev/null | head -5 || echo no_lsof', timeout=10)

print()
print('=== KILL PORT 47300 HOLDER ===')
ssh('fuser -k 47300/tcp 2>/dev/null; echo killed_47300', timeout=10)
time.sleep(3)
ssh('ss -tlnp | grep 47300 || echo PORT_47300_FREE', timeout=10)

print()
print('=== START BOT NOW ===')
ssh(
    'setsid python3 /root/bharat-futures-engine/main.py '
    '> /root/bharat-futures-engine/bot.log 2>&1 < /dev/null &'
    ' && echo BOT_LAUNCHED',
    timeout=10
)
time.sleep(20)

print()
print('=== BOT LOG ===')
ssh('strings /root/bharat-futures-engine/bot.log 2>/dev/null | head -35', timeout=10)

print()
print('=== PROCESS CHECK ===')
ssh('ps aux | grep "bharat-futures-engine/main" | grep -v grep', timeout=10)

print()
print('=== AVAXUSD POSITION ===')
ssh("""cd /root/bharat-futures-engine && python3 -c "
import db
p = db.get_symbol_position('AVAXUSD')
print('POS:', p)
print('running:', db.get_param('algo_running'))
" 2>&1""", timeout=10)
