"""Setup GitHub on VPS — generate SSH key and configure git pull."""
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

def cmd(command, timeout=20):
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

# Step 1: Generate SSH key on VPS (no passphrase, silent)
print("\n[1] Generating SSH key on VPS...")
out = cmd('ssh-keygen -t ed25519 -C "bharat-futures-vps" -f /root/.ssh/github_deploy -N "" 2>&1', timeout=10)
print("   ", out[:200])

# Step 2: Get the public key
print("\n[2] Reading public key...")
pubkey = cmd("cat /root/.ssh/github_deploy.pub")
print("\n   PUBLIC KEY (copy this):")
print("   " + pubkey)

# Step 3: Configure SSH to use this key for GitHub
print("\n[3] Configuring SSH for GitHub...")
ssh_config = """
Host github.com
    HostName github.com
    User git
    IdentityFile /root/.ssh/github_deploy
    StrictHostKeyChecking no
"""
out = cmd(f"echo '{ssh_config}' >> /root/.ssh/config && chmod 600 /root/.ssh/config && echo CONFIG_OK")
print("   ", out)

# Step 4: Check if git is installed
print("\n[4] Checking git...")
out = cmd("git --version || apt-get install -y git 2>&1 | tail -2")
print("   ", out[:100])

# Step 5: Set up git in BHARAT-FUTURES-ENGINE directory
print("\n[5] Initializing git on VPS project dir...")
out = cmd("cd /root/BHARAT-FUTURES-ENGINE && git init && git remote remove origin 2>/dev/null; git remote add origin git@github.com:gurjeetsinghgill8-web/bharat-futures-engine.git && echo GIT_SETUP_OK")
print("   ", out)

# Store pubkey to file for browser step
with open("vps_deploy_key.pub", "w") as f:
    f.write(pubkey)
print(f"\n[SAVED] Public key saved to vps_deploy_key.pub")
print("\nNEXT: Add this key to GitHub as a Deploy Key")
print("KEY:", pubkey)

ssh.close()
