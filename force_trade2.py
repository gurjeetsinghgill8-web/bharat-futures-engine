import subprocess, sys

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def ssh(cmd, timeout=30):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, timeout=timeout
    )
    # Decode safely
    out = r.stdout.decode('utf-8', errors='replace').strip()
    if out:
        # Remove non-ASCII safely for Windows terminal
        safe = out.encode('ascii', errors='replace').decode('ascii')
        print(safe[:1500])
    return r.returncode

print('=== EXECUTE AVAXUSD TRADE ===')
trade_py = """
import sys
sys.stdout.reconfigure(errors='replace')
import futures_executor as fx
import supertrend as st_mod
import db, time

sig, val, close, ts = st_mod.get_supertrend_signal_for_symbol('AVAXUSD', '15m', 20, 1.5)
print('Signal:', sig, 'Close:', close, 'ST:', round(val,4))

if not sig:
    print('ERROR: No signal')
    sys.exit(1)

pid, sym = fx.get_product_id_for_symbol('AVAXUSD')
print('PID:', pid, 'SYM:', sym)

result = fx.execute_trade_for_symbol('AVAXUSD', sig, lots=1, leverage=10)
print('TRADE SENT:', result)

db.update_symbol_position('AVAXUSD', direction=sig, entry_price=close,
                          qty=1, active=1, last_candle_ts=int(time.time()))
print('DB updated')
pos = db.get_symbol_position('AVAXUSD')
print('POSITION:', pos)
"""

# Write to temp file on VPS and execute
ssh(f"echo '{trade_py}' > /tmp/trade_avax.py && cd /root/bharat-futures-engine && python3 /tmp/trade_avax.py 2>&1", timeout=30)

print()
print('=== CHECK BOT LOG ===')
ssh("tail -15 /root/bharat-futures-engine/bot.log 2>/dev/null | strings | head -15", timeout=10)

print()
print('=== AVAX POSITION IN DB ===')
ssh("""cd /root/bharat-futures-engine && python3 -c "import db; print(db.get_symbol_position('AVAXUSD'))" 2>&1""", timeout=10)
