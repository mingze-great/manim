import subprocess
import time

def ssh_command(host, user, password, cmd):
    """使用密码执行 SSH 命令"""
    # 使用 sshpass 如果可用，否则使用 expect 模式
    full_cmd = f'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {user}@{host} "{cmd}"'
    
    proc = subprocess.Popen(
        full_cmd,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 尝试发送密码
    time.sleep(1)
    try:
        proc.stdin.write(password + '\n')
        proc.stdin.flush()
    except:
        pass
    
    stdout, stderr = proc.communicate(timeout=30)
    return stdout, stderr

if __name__ == "__main__":
    host = "106.52.166.109"
    user = "root"
    password = "010421"
    
    # 测试简单命令
    stdout, stderr = ssh_command(host, user, password, "echo 'Connected to dev server' && hostname")
    print("STDOUT:", stdout)
    print("STDERR:", stderr)
