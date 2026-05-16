"""Deploy: git pull, restart bot + dashboard."""
import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('46.224.133.16', username='root', password='U4CJs4HKbMMJ', timeout=20)
def cmd(c, timeout=45):
    ch = ssh.get_transport().open_session(); ch.settimeout(timeout)
    ch.exec_command(c); ch.shutdown_write()
    out = b''
    start = time.time()
    while True:
        if ch.recv_ready(): out += ch.recv(4096)
        if ch.recv_stderr_ready(): out += ch.recv_stderr(4096)
        if ch.exit_status_ready(): break
        if time.time()-start > timeout: break
        time.sleep(0.1)
    return out.decode('utf-8',errors='replace').encode('ascii',errors='replace').decode().strip()

print(cmd('cd /root/BHARAT-FUTURES-ENGINE && git fetch origin && git reset --hard origin/main 2>&1'))
print(cmd('pkill -f "python3.*main.py" 2>/dev/null; fuser -k 47399/tcp 2>/dev/null; sleep 2; echo KILLED'))
cmd('cd /root/BHARAT-FUTURES-ENGINE && nohup python3 -u main.py > bot.log 2>&1 &')
time.sleep(8)
print(cmd('fuser -k 8600/tcp 2>/dev/null; sleep 1; echo KILLED'))
cmd('cd /root/BHARAT-FUTURES-ENGINE && nohup python3 -m streamlit run app.py --server.port 8600 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false > /root/dash_futures.log 2>&1 &')
time.sleep(12)
print(cmd('pgrep -a python3 | grep -E "main.py|8600" | head -3'))
print(cmd('ss -tlnp | grep 8600 | head -1'))
print(cmd('tail -15 /root/BHARAT-FUTURES-ENGINE/bot.log'))
ssh.close()
print('DONE — http://46.224.133.16:8600')
