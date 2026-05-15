import subprocess

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def ssh(cmd, timeout=30):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, text=True, timeout=timeout,
        encoding='utf-8', errors='replace'
    )
    out = (r.stdout + r.stderr).strip()
    if out: print(out[:1200])
    return r.returncode

# ================================================================
# STEP 1: Get AVAXUSD signal right now
# ================================================================
print('=== STEP 1: AVAXUSD LIVE SIGNAL ===')
ssh(r"""cd /root/bharat-futures-engine && python3 -c "
import supertrend as st_mod
import db

sig, val, close, ts = st_mod.get_supertrend_signal_for_symbol('AVAXUSD', '15m', 20, 1.5)
print('SIGNAL  :', sig)
print('ST VALUE:', val)
print('CLOSE   :', close)
print('TS      :', ts)
db.set_param('_avax_signal', str(sig) if sig else 'NONE')
db.set_param('_avax_close',  str(close))
" """)

# ================================================================
# STEP 2: Turn engine ON so BTC bot also runs
# ================================================================
print()
print('=== STEP 2: ENGINE ON ===')
ssh(r"""cd /root/bharat-futures-engine && python3 -c "
import db
db.set_param('algo_running', 'ON')
print('algo_running =', db.get_param('algo_running'))
" """)

# ================================================================
# STEP 3: Execute AVAXUSD trade directly on Delta Exchange
# ================================================================
print()
print('=== STEP 3: EXECUTE AVAXUSD TRADE ON DELTA ===')
ssh(r"""cd /root/bharat-futures-engine && python3 -c "
import supertrend as st_mod
import futures_executor as fx
import db

# Get fresh signal
sig, val, close, ts = st_mod.get_supertrend_signal_for_symbol('AVAXUSD', '15m', 20, 1.5)
print('Signal =', sig, '| Close =', close, '| ST =', val)

if sig is None:
    print('ERROR: No signal from Delta. Check connection.')
else:
    # Get product ID
    pid, sym = fx.get_product_id_for_symbol('AVAXUSD')
    print('Product ID =', pid, 'Symbol =', sym)

    # Execute trade
    result = fx.execute_trade_for_symbol('AVAXUSD', sig, lots=1, leverage=10)
    print('TRADE RESULT:', result)

    # Update DB position
    db.update_symbol_position(
        'AVAXUSD',
        direction=sig,
        entry_price=close,
        qty=1,
        active=1,
        last_candle_ts=int(__import__('time').time())
    )
    print('DB position updated')
    print('DONE: AVAXUSD', sig, 'order sent!')
" """)

# ================================================================
# STEP 4: Verify position in DB
# ================================================================
print()
print('=== STEP 4: VERIFY POSITION ===')
ssh(r"""cd /root/bharat-futures-engine && python3 -c "
import db
pos = db.get_symbol_position('AVAXUSD')
print('AVAXUSD position in DB:', pos)
" """)

print()
print('=== DONE — Check Telegram for confirmation ===')
