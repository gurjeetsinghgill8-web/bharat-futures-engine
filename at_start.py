import subprocess, time

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def sshr(cmd, timeout=20):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, timeout=timeout
    )
    out = r.stdout.decode('utf-8', errors='replace').strip()
    safe = out.encode('ascii', errors='replace').decode('ascii')
    if safe: print(safe[:2000])

# Write a shell script on VPS to start the bot properly
LAUNCH_SCRIPT = r"""#!/bin/bash
export PYTHONUNBUFFERED=1
cd /root/bharat-futures-engine
exec python3 -u main.py >> /root/bharat-futures-engine/bot.log 2>&1
"""

print('=== WRITE LAUNCH SCRIPT ON VPS ===')
sshr(f"cat > /root/start_bot.sh << 'HEREDOC'\n{LAUNCH_SCRIPT}\nHEREDOC", timeout=10)
sshr('chmod +x /root/start_bot.sh && echo SCRIPT_READY', timeout=5)

# Use 'at now' to schedule immediate execution
print()
print('=== START VIA AT COMMAND ===')
sshr('echo "/root/start_bot.sh" | at now 2>&1 || echo AT_FAILED', timeout=10)

time.sleep(20)

print()
print('=== BOT LOG ===')
sshr("""python3 << 'EOF'
try:
    f = open('/root/bharat-futures-engine/bot.log', errors='replace')
    lines = f.readlines()
    print(f'Lines: {len(lines)}')
    for l in lines[:30]:
        clean = ''.join(c if ord(c)<128 else '?' for c in l.rstrip())
        print(clean)
except Exception as e:
    print('Error:', e)
EOF""", timeout=10)

print()
print('=== PROCESS ===')
sshr('ps aux | grep "main.py" | grep -v grep | grep -v BHARAT-ALGO', timeout=10)
