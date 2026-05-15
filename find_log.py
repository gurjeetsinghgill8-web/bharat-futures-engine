import subprocess, time

plink = r'C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\plink.exe'
vps_ip   = '46.224.133.16'
vps_user = 'root'
vps_pass = 'U4CJs4HKbMMJ'
HOSTKEY  = 'ssh-ed25519 255 SHA256:1Kix/hHM8n/DG7y/FuGtIZyB10dZkhw1AeEMeoSDkW0'

def ssh(cmd, timeout=15):
    r = subprocess.run(
        [plink, '-pw', vps_pass, '-batch', '-hostkey', HOSTKEY,
         '-ssh', f'{vps_user}@{vps_ip}', cmd],
        capture_output=True, timeout=timeout
    )
    out = (r.stdout + r.stderr).decode('utf-8', errors='replace').strip()
    safe = out.encode('ascii', errors='replace').decode('ascii')
    if safe: print(safe[:2000])

# Find where PID 91841 is writing output
print('=== PID 91841 FILE DESCRIPTORS ===')
ssh('ls -la /proc/91841/fd/ 2>/dev/null | head -15', timeout=10)

print()
print('=== PID 91841 stdout/stderr (fd 1 and 2) ===')
ssh('readlink /proc/91841/fd/1 2>/dev/null; readlink /proc/91841/fd/2 2>/dev/null', timeout=10)

print()
# Check if DB is being updated (proves bot is running loops)
print('=== DB LAST WRITE TIME ===')
ssh('ls -la /root/bharat-futures-engine/futures_engine.db', timeout=10)

print()
print('=== RECENT FILES MODIFIED ===')
ssh('find /root/bharat-futures-engine -newer /root/bharat-futures-engine/main.py -name "*.log" -o -name "*.db" 2>/dev/null | xargs ls -la 2>/dev/null', timeout=10)
