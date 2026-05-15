"""
Setup VPS to pull from GitHub using HTTPS token.
After this, any update = git push from laptop -> run update on VPS.
"""
import paramiko, time

secrets = {}
for line in open('secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        secrets[k.strip().lower()] = v.strip()

GITHUB_TOKEN = secrets.get('github_token', 'YOUR_GITHUB_PAT_HERE')
GITHUB_USER  = "gurjeetsinghgill8-web"
REPO_URL     = f"https://{GITHUB_USER}:{GITHUB_TOKEN}@github.com/{GITHUB_USER}/bharat-futures-engine.git"
REMOTE       = "/root/BHARAT-FUTURES-ENGINE"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('46.224.133.16', username='root', password=secrets['vps_password'], timeout=20)
print("Connected to VPS!")

def cmd(command, timeout=30):
    transport = ssh.get_transport()
    channel = transport.open_session()
    channel.settimeout(timeout)
    channel.exec_command(command)
    channel.shutdown_write()
    out = b""; err = b""
    start = time.time()
    while True:
        if channel.recv_ready():        out += channel.recv(4096)
        if channel.recv_stderr_ready(): err += channel.recv_stderr(4096)
        if channel.exit_status_ready(): break
        if time.time() - start > timeout: break
        time.sleep(0.1)
    return out.decode('utf-8', errors='replace').strip()

# Step 1: Configure git in the project directory
print("\n[1] Setting up git remote with HTTPS token...")
out = cmd(f"""
cd {REMOTE} &&
git config --global user.email "gurjeetsinghgill8@gmail.com" &&
git config --global user.name "Gurjeet Singh Gill" &&
git remote remove origin 2>/dev/null;
git remote add origin '{REPO_URL}' &&
echo REMOTE_OK
""")
print("   ", out)

# Step 2: Fetch from GitHub and reset to match remote
print("\n[2] Pulling latest code from GitHub...")
out = cmd(f"""
cd {REMOTE} &&
git fetch origin 2>&1 | tail -5 &&
git reset --hard origin/main 2>&1 | tail -5
""", timeout=60)
print(out[:500])

# Step 3: Verify files are updated
print("\n[3] Checking files on VPS:")
out = cmd(f"ls {REMOTE}/ | head -20")
print(out)

# Step 4: Create a one-click update script on the VPS
print("\n[4] Creating update script on VPS...")
update_script = f"""#!/bin/bash
# BHARAT FUTURES ENGINE - One-click update from GitHub
echo "Updating from GitHub..."
cd {REMOTE}
git fetch origin
git reset --hard origin/main
echo "Restarting bot..."
fuser -k 47399/tcp 2>/dev/null
pkill -f main.py 2>/dev/null
sleep 2
nohup python3 -u main.py > bot.log 2>&1 &
sleep 5
pgrep -f main.py && echo "BOT RUNNING OK" || echo "BOT FAILED - check bot.log"
"""
out = cmd(f"cat > /root/update_bot.sh << 'EOF'\n{update_script}\nEOF\nchmod +x /root/update_bot.sh && echo SCRIPT_CREATED")
print("   ", out)

# Step 5: Restart bot with fresh code
print("\n[5] Restarting bot with latest code...")
out = cmd(f"fuser -k 47399/tcp 2>/dev/null; pkill -f main.py 2>/dev/null; sleep 3; echo KILLED")
print("   ", out)
time.sleep(3)

out = cmd(f"cd {REMOTE} && nohup python3 -u main.py > bot.log 2>&1 &", timeout=5)
time.sleep(8)

# Step 6: Verify
print("\n[6] Bot status:")
out = cmd("ss -tlnp | grep 47399 || echo PORT_FREE")
if "python3" in out:
    print("    BOT RUNNING - port 47399 held")
else:
    print("    Checking log...")
    out = cmd(f"tail -20 {REMOTE}/bot.log")
    print(out.encode('ascii','replace').decode())

ssh.close()
print("\n" + "="*55)
print("GITHUB -> VPS PIPELINE SETUP COMPLETE!")
print("="*55)
print("\nFUTURE UPDATES (I do this for you):")
print("  1. Make code changes on laptop")
print("  2. git push (already configured)")
print("  3. Run: python update_vps_from_github.py")
print("     OR on VPS: /root/update_bot.sh")
print("\nNO MORE SCP, NO MORE VPN, NO MORE DELAYS!")
