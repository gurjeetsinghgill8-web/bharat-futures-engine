import subprocess, time

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def ssh(cmd, timeout=20):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch',
         '-hostkey', HOSTKEY, '-ssh',
         f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, text=True, timeout=timeout
    )
    out = (r.stdout + r.stderr).strip()
    if out: print(out[-600:])
    return r.returncode

print('=== KILLING OLD PORT 8600 PROCESS ===')
# Kill specifically port 8600 occupant
ssh('fuser -k 8600/tcp; echo port_cleared', timeout=15)
time.sleep(3)

# Also kill all streamlit instances
ssh('pkill -9 -f streamlit; pkill -9 -f main.py; echo all_killed', timeout=15)
time.sleep(3)

print()
print('=== STARTING BHARAT NEXUS v6.0 ===')

# Start bot in background
ssh('setsid python3 /root/bharat-futures-engine/main.py > /root/bharat-futures-engine/bot.log 2>&1 < /dev/null &', timeout=10)
time.sleep(2)

# Start dashboard
ssh(
    'setsid python3 -m streamlit run /root/bharat-futures-engine/app.py '
    '--server.port 8600 --server.headless true --server.address 0.0.0.0 '
    '> /root/bharat-futures-engine/dash.log 2>&1 < /dev/null &',
    timeout=10
)
time.sleep(8)

print()
print('=== VERIFYING ===')
ssh('ps aux | grep -E "bharat-futures|streamlit" | grep -v grep | head -6', timeout=10)
ssh('ss -tlnp | grep 8600 || echo port_8600_not_yet_bound', timeout=10)
ssh('tail -8 /root/bharat-futures-engine/dash.log 2>/dev/null', timeout=10)

print()
print('Dashboard: http://46.224.133.16:8600')
