"""Permanently remove PAPER mode — hardcode LIVE everywhere."""
import os

BASE = r'c:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE'
files = ['futures_executor.py', 'main.py', 'app.py', 'analytics.py']

replacements = [
    # All PAPER fallback defaults → hardcoded "LIVE"
    ("db.get_param('trade_mode', 'PAPER')",   '"LIVE"'),
    ('db.get_param("trade_mode", "PAPER")',    '"LIVE"'),
    # Startup: stop setting PAPER as default
    ('db.set_param("trade_mode",       "PAPER")', 'db.set_param("trade_mode",       "LIVE")'),
    # Dashboard selectbox default index
    ('index=0 if trade_mode=="PAPER" else 1',  'index=1'),
]

for fname in files:
    path = os.path.join(BASE, fname)
    if not os.path.exists(path):
        print(f'SKIP (not found): {fname}')
        continue
    with open(path, 'r', encoding='utf-8') as f:
        code = f.read()
    original = code
    for old, new in replacements:
        code = code.replace(old, new)
    if code != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(code)
        print(f'UPDATED: {fname}')
    else:
        print(f'no change: {fname}')

print('\nAll PAPER defaults permanently replaced with LIVE.')
