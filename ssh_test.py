import subprocess
import sys

password = "010421"
host = "106.52.166.109"
user = "root"

commands = [
    "echo '=== 开发服务器连接成功 ==='",
    "cd /opt/manim-dev && git branch --show-current",
    "cd /opt/manim-dev && git log --oneline -3",
    "ps aux | grep uvicorn | grep -v grep"
]

cmd = f'ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no {user}@{host} "{"; ".join(commands)}"'

print(f"Connecting to {host}...")
print(f"Command: {cmd}")
