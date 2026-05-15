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

print('=== CLEARING LOCK + RESTARTING ===')

# 1. Clear the lock file
ssh('rm -f /tmp/bharat_algo.lock; echo LOCK_CLEARED', timeout=10)

# 2. Kill any lingering bharat-futures main.py
ssh('for pid in $(pgrep -f "bharat-futures-engine/main.py"); do kill -9 $pid; done; echo OLD_BOTS_KILLED', timeout=10)

time.sleep(3)

# 3. Start bot fresh
ssh(
    'setsid python3 /root/bharat-futures-engine/main.py '
    '> /root/bharat-futures-engine/bot.log 2>&1 < /dev/null &'
    ' && echo BOT_LAUNCHED',
    timeout=10
)

time.sleep(20)

# 4. Check log
print()
print('=== BOT LOG (first 30 lines) ===')
ssh('strings /root/bharat-futures-engine/bot.log 2>/dev/null | head -30', timeout=10)

# 5. Check process
print()
print('=== BOT PROCESS ===')
ssh('ps aux | grep "bharat-futures-engine/main.py" | grep -v grep', timeout=10)

# 6. Check AVAXUSD position
print()
print('=== AVAXUSD POSITION ===')
ssh("""cd /root/bharat-futures-engine && python3 -c "
import db
p = db.get_symbol_position('AVAXUSD')
if p:
    print('active=', p['active'], 'dir=', p['direction'], 'entry=', p['entry_price'])
else:
    print('No position yet')
" 2>&1""", timeout=10)
