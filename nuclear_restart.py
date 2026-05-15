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
    out = (r.stdout + r.stderr).decode('utf-8', errors='replace').strip()
    safe = out.encode('ascii', errors='replace').decode('ascii')
    if safe: print(safe[:1500])

print('=== WHAT IS ON PORT 47300 RIGHT NOW? ===')
ssh('ss -tlnp | grep 47300', timeout=10)
ssh('lsof -i TCP:47300 2>/dev/null | head -5', timeout=10)
ssh('fuser 47300/tcp 2>/dev/null && echo HAS_PROCESS || echo PORT_FREE', timeout=10)

print()
print('=== ALL PYTHON PROCESSES ===')
ssh('ps aux | grep python3 | grep -v grep | grep -v streamlit | grep -v networkd | grep -v unattended', timeout=10)

print()
print('=== NUCLEAR KILL ALL PYTHON + RESTART ===')
# Kill EVERYTHING python that is not system or venv
ssh("""
for pid in $(ps aux | grep python3 | grep -v grep | grep -v '/root/BHARAT-ALGO' | grep -v 'networkd' | grep -v 'unattended' | awk '{print $2}'); do
    echo "Killing $pid"
    kill -9 $pid 2>/dev/null
done
echo NUCLEAR_DONE
""", timeout=15)

time.sleep(5)

print()
print('=== PORT AFTER NUCLEAR KILL ===')
ssh('ss -tlnp | grep 47300 && echo STILL_BUSY || echo PORT_FREE', timeout=10)

print()
print('=== START BOT ===')
ssh('setsid python3 /root/bharat-futures-engine/main.py > /tmp/bot_fresh.txt 2>&1 < /dev/null &', timeout=10)
time.sleep(15)

print()
print('=== BOT OUTPUT ===')
ssh('cat /tmp/bot_fresh.txt | iconv -f utf8 -t ascii//TRANSLIT 2>/dev/null | head -30', timeout=10)

print()
print('=== RUNNING NOW ===')
ssh('ps aux | grep "bharat-futures" | grep -v grep', timeout=10)
