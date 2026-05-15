import subprocess

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def sshr(cmd, timeout=15):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, timeout=timeout
    )
    out = r.stdout.decode('utf-8', errors='replace').strip()
    if out: print(out[:2000])

print('=== BOT STATUS ===')
sshr('ps aux | grep "bharat-futures-engine/main" | grep -v grep', timeout=10)
sshr('ss -tlnp | grep 47399 || echo port_free', timeout=10)
sshr("""python3 -c "
f=open('/root/bharat-futures-engine/bot.log', errors='replace')
lines=f.readlines()
print('LOG LINES:', len(lines))
for l in lines[-20:]:
    print(l.rstrip())
" 2>&1""", timeout=10)
sshr("""cd /root/bharat-futures-engine && python3 -c "
import db
p = db.get_symbol_position('AVAXUSD')
print('AVAX:', p)
" 2>&1""", timeout=10)
