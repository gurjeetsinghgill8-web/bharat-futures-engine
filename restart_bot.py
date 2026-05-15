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
    if out:
        safe = out.encode('ascii', errors='replace').decode('ascii')
        print(safe[:800])
    return r.returncode

def upload(fname):
    r = subprocess.run(
        [pscp, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         f'{src}\\{fname}',
         f'{vps_user}@{vps_ip}:/root/bharat-futures-engine/'],
        capture_output=True, text=True, timeout=20
    )
    print(f'  {fname}: {"OK" if r.returncode==0 else "FAIL"}')

print('=== UPLOADING FIXED FILES ===')
upload('main.py')
upload('app.py')

print()
print('=== RESTARTING BOT ===')
# Kill the old bot (PID from our engine)
ssh('pkill -9 -f "bharat-futures-engine/main.py" 2>/dev/null; echo bot_killed', timeout=10)
time.sleep(2)

# Start fresh bot
ssh(
    'setsid python3 /root/bharat-futures-engine/main.py '
    '> /root/bharat-futures-engine/bot.log 2>&1 < /dev/null &',
    timeout=10
)
time.sleep(8)

print()
print('=== BOT LOG (first trade signals) ===')
ssh('strings /root/bharat-futures-engine/bot.log 2>/dev/null | tail -20', timeout=10)

print()
print('=== AVAXUSD POSITION ===')
ssh("""cd /root/bharat-futures-engine && python3 -c "import db; p=db.get_symbol_position('AVAXUSD'); print('active=',p['active'] if p else 'None', 'dir=',p['direction'] if p else 'None')" 2>&1""", timeout=10)

print()
print('=== DONE ===')
