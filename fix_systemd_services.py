"""Check systemd service and fix dashboard via systemd."""
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

p("=== SYSTEMD SERVICE INVESTIGATION ===")

# Read the existing service files
p("\n[1] bharat_futures_dash.service:")
p(cmd("cat /etc/systemd/system/bharat_futures_dash.service"))

p("\n[2] bharat_futures_bot.service:")
p(cmd("cat /etc/systemd/system/bharat_futures_bot.service"))

p("\n[3] Current status of futures services:")
p(cmd("systemctl status bharat_futures_dash.service --no-pager | head -20"))
p(cmd("systemctl status bharat_futures_bot.service --no-pager | head -15"))

# Update service files to point to our new code
p("\n[4] Updating bharat_futures_dash.service to use BHARAT-FUTURES-ENGINE...")

new_dash_service = """[Unit]
Description=Bharat Futures Dashboard
After=network.target

[Service]
User=root
WorkingDirectory=/root/BHARAT-FUTURES-ENGINE
ExecStart=/usr/bin/python3 -m streamlit run app.py --server.port 8600 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false
Restart=always
RestartSec=10
Environment=PYTHONPATH=/root/BHARAT-FUTURES-ENGINE

[Install]
WantedBy=multi-user.target
"""

# Write service file
cmd(f"cat > /etc/systemd/system/bharat_futures_dash.service << 'SVCEOF'\n{new_dash_service}\nSVCEOF")

# Update bot service too
new_bot_service = """[Unit]
Description=Bharat Futures Engine Bot
After=network.target

[Service]
User=root
WorkingDirectory=/root/BHARAT-FUTURES-ENGINE
ExecStart=/usr/bin/python3 -u main.py
Restart=always
RestartSec=15
Environment=PYTHONPATH=/root/BHARAT-FUTURES-ENGINE

[Install]
WantedBy=multi-user.target
"""
cmd(f"cat > /etc/systemd/system/bharat_futures_bot.service << 'SVCEOF'\n{new_bot_service}\nSVCEOF")

# Kill nohup processes and use systemd instead
p("\n[5] Stopping nohup processes, starting via systemd...")
cmd("fuser -k 47399/tcp 2>/dev/null; fuser -k 8600/tcp 2>/dev/null; sleep 2")
cmd("systemctl daemon-reload")
p(cmd("systemctl restart bharat_futures_bot.service && echo BOT_SERVICE_STARTED || echo BOT_SERVICE_FAILED"))
time.sleep(5)
p(cmd("systemctl restart bharat_futures_dash.service && echo DASH_SERVICE_STARTED || echo DASH_SERVICE_FAILED"))
time.sleep(8)

p("\n[6] Final status:")
p(cmd("systemctl is-active bharat_futures_bot.service; systemctl is-active bharat_futures_dash.service"))
p(cmd("ss -tlnp | grep -E '47399|8600'"))
p(cmd("tail -5 /root/BHARAT-FUTURES-ENGINE/bot.log"))

ssh.close()
p("\nDone. Now adding port 8600 to Hostasia cloud firewall via browser...")
