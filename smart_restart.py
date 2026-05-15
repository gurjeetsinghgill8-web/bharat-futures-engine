import subprocess, time

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
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

print('=== KILL ALL ORPHAN BOTS (every main.py except BHARAT-ALGO) ===')

# Kill all processes running main.py that are NOT from BHARAT-ALGO-TRADING-APP
ssh("""
for pid in $(pgrep -f "main.py"); do
    cmd=$(cat /proc/$pid/cmdline 2>/dev/null | strings | tr '\\n' ' ')
    if echo "$cmd" | grep -q "BHARAT-ALGO"; then
        echo "SKIP: $pid (BHARAT-ALGO-TRADING-APP)"
    else
        echo "KILL: $pid ($cmd)"
        kill -9 $pid 2>/dev/null
    fi
done
echo DONE_KILLING
""", timeout=15)

time.sleep(3)

print()
print('=== VERIFY PORT 47300 FREE ===')
ssh('ss -tlnp | grep 47300 && echo PORT_BUSY || echo PORT_FREE', timeout=10)

print()
print('=== START BOT ===')
ssh(
    'setsid python3 /root/bharat-futures-engine/main.py '
    '> /root/bharat-futures-engine/bot.log 2>&1 < /dev/null &'
    ' && echo BOT_STARTED',
    timeout=10
)

time.sleep(20)

print()
print('=== BOT LOG ===')
ssh('strings /root/bharat-futures-engine/bot.log 2>/dev/null | head -40', timeout=10)

print()
print('=== PROCESSES ===')
ssh('ps aux | grep main.py | grep -v grep', timeout=10)
