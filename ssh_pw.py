import subprocess
import sys
import select
import time

host = "106.52.166.109"
user = "root"
password = "010421"

print(f"Connecting to {user}@{host}...")

# 使用 pexpect 风格的交互
import subprocess
import threading
import queue

def run_ssh():
    cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "PreferredAuthentications=password",
        "-o", "PubkeyAuthentication=no",
        f"{user}@{host}",
        "echo 'CONNECTED' && cd /opt/manim-dev && git branch --show-current && git log --oneline -3"
    ]
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # 等待密码提示
    time.sleep(2)
    
    # 发送密码
    try:
        proc.stdin.write(password + '\n')
        proc.stdin.flush()
    except Exception as e:
        print(f"Error sending password: {e}")
    
    # 读取输出
    try:
        stdout, stderr = proc.communicate(timeout=30)
        print("=== STDOUT ===")
        print(stdout)
        if stderr:
            print("=== STDERR ===")
            print(stderr)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("Timeout!")

if __name__ == "__main__":
    run_ssh()
