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
    out = (r.stdout + r.stderr).decode('utf-8', errors='replace').strip()
    safe = out.encode('ascii', errors='replace').decode('ascii')
    if safe: print(safe[:2000])

print('Waiting 35 seconds for first loop cycle...')
time.sleep(35)

print('=== BOT LOG ===')
ssh('cat /tmp/bot_fresh.txt | iconv -f utf8 -t ascii//TRANSLIT 2>/dev/null | tail -30', timeout=10)
ssh('cat /root/bharat-futures-engine/bot.log | iconv -f utf8 -t ascii//TRANSLIT 2>/dev/null | tail -30', timeout=10)

print()
print('=== AVAXUSD POSITION ===')
ssh("""cd /root/bharat-futures-engine && python3 -c "
import db
p = db.get_symbol_position('AVAXUSD')
print('active:', p['active'] if p else None)
print('dir:', p['direction'] if p else None)
print('entry:', p['entry_price'] if p else None)
print('algo:', db.get_param('algo_running'))
" 2>&1""", timeout=10)

print()
print('=== BOT RUNNING ===')
ssh('ps aux | grep "bharat-futures-engine/main.py" | grep -v grep', timeout=10)
