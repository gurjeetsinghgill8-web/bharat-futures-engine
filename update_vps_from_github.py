"""Pull latest from GitHub and restart bot + dashboard on VPS."""
import paramiko, time

secrets = {}
for line in open('secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        secrets[k.strip().lower()] = v.strip()

GITHUB_USER  = "gurjeetsinghgill8-web"
GITHUB_TOKEN = secrets.get('github_token', 'YOUR_GITHUB_PAT_HERE')
REPO_URL     = f"https://{GITHUB_USER}:{GITHUB_TOKEN}@github.com/{GITHUB_USER}/bharat-futures-engine.git"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('46.224.133.16', username='root', password=secrets['vps_password'], timeout=20)
print("Connected!")

def cmd(c, timeout=30):
    transport = ssh.get_transport()
    ch = transport.open_session()
    ch.settimeout(timeout)
    ch.exec_command(c)
    ch.shutdown_write()
    out = b""; err = b""
    start = time.time()
    while True:
        if ch.recv_ready(): out += ch.recv(4096)
        if ch.recv_stderr_ready(): err += ch.recv_stderr(4096)
        if ch.exit_status_ready(): break
        if time.time()-start > timeout: break
        time.sleep(0.1)
    return out.decode('utf-8', errors='replace').strip()

print("\n[1] git pull from GitHub...")
out = cmd(f"cd /root/BHARAT-FUTURES-ENGINE && git remote set-url origin '{REPO_URL}' && git fetch origin && git reset --hard origin/main 2>&1", timeout=30)
print(out[:300])

print("\n[2] Kill old bot + dashboard...")
out = cmd("fuser -k 47399/tcp 2>/dev/null; fuser -k 8501/tcp 2>/dev/null; sleep 2; echo KILLED")
print("  ", out)

print("\n[3] Start bot...")
cmd("cd /root/BHARAT-FUTURES-ENGINE && nohup python3 -u main.py > bot.log 2>&1 &")
time.sleep(6)

print("\n[4] Start dashboard...")
cmd("cd /root/BHARAT-FUTURES-ENGINE && nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true > dashboard.log 2>&1 &")
time.sleep(5)

print("\n[5] Status:")
out = cmd("ss -tlnp | grep -E '47399|8501' || echo NONE")
print(out.encode('ascii','replace').decode())

print("\n[6] Bot log (last 10):")
out = cmd("tail -10 /root/BHARAT-FUTURES-ENGINE/bot.log")
print(out.encode('ascii','replace').decode())

ssh.close()
print("\nDONE — PAPER MODE PERMANENTLY REMOVED FROM VPS")
