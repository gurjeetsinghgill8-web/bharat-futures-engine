"""Find TF setting and fix dashboard port on VPS."""
import paramiko, time, sys

secrets = {}
for line in open('secrets.txt'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        secrets[k.strip().lower()] = v.strip()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('46.224.133.16', username='root', password=secrets['vps_password'], timeout=20)

def p(text): sys.stdout.buffer.write((str(text)[:600]+'\n').encode('utf-8', errors='replace')); sys.stdout.flush()
def cmd(c, timeout=15):
    ch = ssh.get_transport().open_session()
    ch.settimeout(timeout); ch.exec_command(c); ch.shutdown_write()
    out = b""
    start = time.time()
    while True:
        if ch.recv_ready(): out += ch.recv(4096)
        if ch.recv_stderr_ready(): ch.recv_stderr(4096)
        if ch.exit_status_ready(): break
        if time.time()-start > timeout: break
        time.sleep(0.1)
    return out.decode('utf-8', errors='replace').strip()

p("Connected!")

# 1. Find TF settings
p("[1] Candle resolution in main.py:")
p(cmd("grep -n 'resolution\\|5m\\|15m\\|candle' /root/BHARAT-FUTURES-ENGINE/main.py | head -20"))

p("[2] supertrend.py resolution:")
p(cmd("grep -n 'resolution\\|5m\\|15m\\|period\\|multiplier' /root/BHARAT-FUTURES-ENGINE/supertrend.py | head -15"))

p("[3] utils.py resolution:")
p(cmd("grep -n 'resolution\\|5m\\|15m' /root/BHARAT-FUTURES-ENGINE/utils.py | head -10"))

# 2. Move dashboard to port 8600
p("[4] Moving dashboard to port 8600...")
cmd("fuser -k 8501/tcp 2>/dev/null; fuser -k 8600/tcp 2>/dev/null; sleep 1")
cmd("cd /root/BHARAT-FUTURES-ENGINE && nohup streamlit run app.py --server.port 8600 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false > dashboard.log 2>&1 &")
time.sleep(5)
p(cmd("ss -tlnp | grep 8600 || echo NOT_ON_8600"))
cmd("iptables -I INPUT -p tcp --dport 8600 -j ACCEPT 2>/dev/null")
p("iptables: port 8600 opened")
p(cmd("curl -s --connect-timeout 3 http://127.0.0.1:8600 | head -c 80 || echo FAIL"))

ssh.close()
p("Done! Dashboard at: http://46.224.133.16:8600")
