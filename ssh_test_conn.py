import subprocess
import sys

# 尝试使用 sshpass 替代方案
# 在 Windows 上，我们可以使用 plink 或 Python 的 paramiko

print("Testing Python SSH connection...")

# 方法1: 尝试导入 paramiko
try:
    import paramiko
    print("paramiko available, using paramiko...")
    
    host = "106.52.166.109"
    user = "root"
    password = "010421"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, port=22, username=user, password=password, timeout=30)
        print("Connected successfully!")
        
        stdin, stdout, stderr = ssh.exec_command("echo '=== 开发服务器信息 ===' && cd /opt/manim-dev && git branch --show-current && git log --oneline -3 && ps aux | grep uvicorn | grep -v grep | head -2")
        
        print("=== OUTPUT ===")
        print(stdout.read().decode())
        
        err = stderr.read().decode()
        if err:
            print("=== STDERR ===")
            print(err)
        
        ssh.close()
        
    except Exception as e:
        print(f"Connection error: {e}")
        
except ImportError:
    print("paramiko not available, trying subprocess...")
    
    # 方法2: 使用 subprocess 和 pexpect
    import time
    import threading
    
    def ssh_with_password():
        proc = subprocess.Popen(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", 
             "root@106.52.166.109", "echo CONNECTED"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        time.sleep(2)
        proc.stdin.write("010421\n")
        proc.stdin.flush()
        
        stdout, stderr = proc.communicate(timeout=30)
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
    
    ssh_with_password()
