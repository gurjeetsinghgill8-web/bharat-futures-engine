import subprocess

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def ssh(cmd, timeout=15):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, text=True, timeout=timeout
    )
    if r.stdout.strip(): print(r.stdout.strip()[:600])
    return r.returncode

print('=== RESTORING VPS SETTINGS ===')

# Set LIVE mode in VPS DB
ssh("cd /root/bharat-futures-engine && python3 -c \"import db; db.set_param('trade_mode','LIVE'); db.set_param('algo_running','OFF'); print('Settings OK')\"")

# Show current settings
ssh("cd /root/bharat-futures-engine && python3 -c \"import db; print('mode=',db.get_param('trade_mode','?')); print('running=',db.get_param('algo_running','?')); print('symbols=',db.get_all_symbols())\"")

# Check bot log
print()
print('=== BOT LOG (last 15 lines) ===')
ssh('tail -15 /root/bharat-futures-engine/bot.log 2>/dev/null || echo no_bot_log', timeout=10)

print()
print('=== DASH LOG (last 10 lines) ===')
ssh('tail -10 /root/bharat-futures-engine/dash.log 2>/dev/null || echo no_dash_log', timeout=10)
