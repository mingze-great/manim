import wexpect
import time
import sys

host = "106.52.166.109"
user = "root"
password = "010421"

print(f"Connecting to {host}...")

try:
    child = wexpect.spawn(f'ssh -o StrictHostKeyChecking=no {user}@{host}')
    
    # 等待密码提示
    child.expect('password:', timeout=30)
    print("Got password prompt, sending password...")
    
    child.sendline(password)
    
    # 等待 shell 提示符
    child.expect(['#', '$'], timeout=30)
    print("Connected successfully!")
    
    # 执行命令
    commands = [
        "echo '=== 开发服务器信息 ==='",
        "cd /opt/manim-dev && git branch --show-current",
        "cd /opt/manim-dev && git log --oneline -3",
        "ps aux | grep uvicorn | grep -v grep | head -2"
    ]
    
    for cmd in commands:
        child.sendline(cmd)
        child.expect(['#', '$'], timeout=10)
        print(child.before.decode() if isinstance(child.before, bytes) else child.before)
    
    child.sendline('exit')
    child.close()
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
