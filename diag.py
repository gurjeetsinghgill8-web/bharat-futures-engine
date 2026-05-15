import subprocess

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def ssh(cmd, timeout=25):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, text=True, timeout=timeout,
        encoding='utf-8', errors='replace'
    )
    if r.stdout.strip(): print(r.stdout.strip()[:1000])
    return r.returncode

print('=== VPS FULL DIAGNOSIS ===')
print()

print('--- Running processes ---')
ssh('ps aux | grep -E "python3 main|streamlit" | grep -v grep')

print()
print('--- DB State ---')
ssh("""cd /root/bharat-futures-engine && python3 -c "
import db
print('algo_running =', db.get_param('algo_running', '?'))
print('trade_mode   =', db.get_param('trade_mode', '?'))
print('candle_tf    =', db.get_param('candle_tf', '?'))
print('st_period    =', db.get_param('st_period', '?'))
print('st_mult      =', db.get_param('st_multiplier', '?'))
print('api_key      =', db.get_param('delta_api_key','')[:12] + '...')
print('symbols      =', db.get_all_symbols())
" """)

print()
print('--- Bot Log (last 20 lines) ---')
ssh('tail -20 /root/bharat-futures-engine/bot.log 2>/dev/null || echo NO_BOT_LOG')

print()
print('--- AVAXUSD Live Signal ---')
ssh("""cd /root/bharat-futures-engine && python3 -c "
import supertrend as st
sig, val, close, ts = st.get_supertrend_signal_for_symbol('AVAXUSD', '15m', 20, 1.5)
print('Signal:', sig, '| ST:', val, '| Close:', close, '| ts:', ts)
" """)
