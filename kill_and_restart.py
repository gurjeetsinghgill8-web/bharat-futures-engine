"""Kill port 47399 lock holder, restart fresh bot on VPS."""
import paramiko, time

secrets = {}
for line in open('secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        secrets[k.strip().lower()] = v.strip()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('46.224.133.16', username='root', password=secrets['vps_password'], timeout=20)
print("Connected to VPS!")

def cmd(command, timeout=15):
    """Run command on VPS with timeout."""
    transport = ssh.get_transport()
    channel = transport.open_session()
    channel.settimeout(timeout)
    channel.exec_command(command)
    channel.shutdown_write()
    out = b""
    err = b""
    start = time.time()
    while True:
        if channel.recv_ready():
            out += channel.recv(4096)
        if channel.recv_stderr_ready():
            err += channel.recv_stderr(4096)
        if channel.exit_status_ready():
            break
        if time.time() - start > timeout:
            break
        time.sleep(0.1)
    return out.decode('utf-8', errors='replace').strip()

# 1. Kill the process holding port 47399 (the socket lock)
print("\n[1] Killing process holding port 47399...")
r = cmd("fuser -k 47399/tcp 2>/dev/null; echo done", timeout=10)
print("   ", r)

# 2. Kill any remaining main.py processes
print("\n[2] Killing any main.py processes...")
r = cmd("pkill -f main.py 2>/dev/null; sleep 1; echo done", timeout=10)
print("   ", r)

# 3. Confirm nothing on port 47399
print("\n[3] Checking port 47399 is free...")
r = cmd("ss -tlnp | grep 47399 || echo PORT_FREE", timeout=5)
print("   ", r)

# 4. Start fresh
print("\n[4] Starting new bot...")
r = cmd("cd /root/BHARAT-FUTURES-ENGINE && nohup python3 main.py >> bot.log 2>&1 &", timeout=5)
time.sleep(8)

# 5. Verify
print("\n[5] Verifying...")
r = cmd("pgrep -la main.py || echo NOT_RUNNING", timeout=5)
print("   ", r)

# 6. Show log
print("\n[6] Bot log (last 20 lines):")
print("-" * 55)
r = cmd("tail -20 /root/BHARAT-FUTURES-ENGINE/bot.log", timeout=10)
print(r)
print("-" * 55)

ssh.close()
print("\nDONE")
