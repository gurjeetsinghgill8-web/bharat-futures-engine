"""Check old BHARAT-ALGO-TRADING-APP config that worked on port 8600."""
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

def p(t): sys.stdout.buffer.write((str(t)[:800]+'\n').encode('utf-8','replace')); sys.stdout.flush()
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

p("=== CHECKING OLD BHARAT-ALGO-TRADING-APP ===")

# 1. What's in the old app directory?
p("\n[1] Old app directory:")
p(cmd("ls /root/BHARAT-ALGO-TRADING-APP/ 2>/dev/null || ls /root/ | grep -i bharat"))

# 2. How was the old dashboard started? Check systemd/startup scripts
p("\n[2] Systemd services:")
p(cmd("systemctl list-units --type=service | grep -i bharat || echo NONE"))

p("\n[3] Startup scripts in /etc/rc.local or crontab:")
p(cmd("cat /etc/rc.local 2>/dev/null; crontab -l 2>/dev/null"))

# 3. Check old streamlit config
p("\n[4] Old streamlit config in BHARAT-ALGO-TRADING-APP:")
p(cmd("cat /root/BHARAT-ALGO-TRADING-APP/.streamlit/config.toml 2>/dev/null || echo NO_CONFIG"))

# 4. Check if there's an nginx/apache reverse proxy
p("\n[5] Nginx/Apache:")
p(cmd("nginx -t 2>&1 | head -3; cat /etc/nginx/sites-enabled/* 2>/dev/null | head -30 || echo NO_NGINX"))

# 5. Full iptables rules — what IS actually open
p("\n[6] Full iptables rules:")
p(cmd("iptables -L INPUT -n -v | head -30"))

# 6. What ports are listening externally
p("\n[7] All listening ports (0.0.0.0):")
p(cmd("ss -tlnp | grep '0.0.0.0'"))

# 7. Check UFW firewall
p("\n[8] UFW firewall status:")
p(cmd("ufw status 2>/dev/null || echo UFW_NOT_INSTALLED"))

# 8. Check if there's an old startup script
p("\n[9] Old startup scripts:")
p(cmd("cat /root/start_dashboard.sh 2>/dev/null; cat /root/BHARAT-ALGO-TRADING-APP/start.sh 2>/dev/null || echo NONE"))

ssh.close()
