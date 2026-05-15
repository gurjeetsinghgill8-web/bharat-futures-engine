import subprocess

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def ssh(cmd, timeout=20):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, text=True, timeout=timeout,
        encoding='utf-8', errors='replace'
    )
    if r.stdout.strip(): print(r.stdout.strip()[:800])
    return r.returncode

# Big Python command to restore all settings at once
restore_cmd = r"""cd /root/bharat-futures-engine && python3 << 'PYEOF'
import db

# ── BTC Engine Settings (match what user had) ──────────────────
db.set_param('candle_tf',         '15m')
db.set_param('st_period',         '20')
db.set_param('st_multiplier',     '1.5')
db.set_param('stop_loss_pct',     '10.0')
db.set_param('trade_mode',        'LIVE')
db.set_param('trade_size',        '1')
db.set_param('leverage',          '10')
db.set_param('cooldown_seconds',  '900')
db.set_param('algo_running',      'OFF')   # User presses START from dashboard

# ── Load API keys from secrets.txt ────────────────────────────
try:
    cfg = {}
    with open('secrets.txt') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            cfg[k.strip()] = v.strip()
    db.set_param('delta_api_key',    cfg.get('DELTA_API_KEY', ''))
    db.set_param('delta_api_secret', cfg.get('DELTA_API_SECRET', ''))
    db.set_param('telegram_token',   cfg.get('TELEGRAM_TOKEN', ''))
    db.set_param('telegram_chat_id', cfg.get('TELEGRAM_CHAT_ID', ''))
    print('API keys loaded from secrets.txt')
except Exception as e:
    print(f'secrets.txt load error: {e}')

# ── Enable AVAXUSD ─────────────────────────────────────────────
db.add_symbol('AVAXUSD', '15m', 20, 1.5, 1, 1)  # enabled=1, multiplier=1.5
print('AVAXUSD enabled')

# ── Verify ────────────────────────────────────────────────────
print('mode =', db.get_param('trade_mode'))
print('tf   =', db.get_param('candle_tf'))
print('P    =', db.get_param('st_period'))
print('M    =', db.get_param('st_multiplier'))
print('key  =', db.get_param('delta_api_key','')[:10] + '...')
print('syms =', db.get_all_symbols())
PYEOF"""

print('=== RESTORING ALL VPS SETTINGS ===')
ssh(restore_cmd, timeout=30)
print()
print('Settings restored!')
