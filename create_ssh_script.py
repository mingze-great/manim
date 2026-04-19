import subprocess
import sys
import os

# 使用环境变量传递密码给 sshpass 风格的连接
# 或者直接使用 PowerShell

host = "106.52.166.109"
user = "root"
password = "010421"

# 创建一个 PowerShell 脚本来处理 SSH 连接
ps_script = f'''
$pass = ConvertTo-SecureString "{password}" -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential ("{user}", $pass)

# 使用 .NET 的 SSH 库
Add-Type -AssemblyName System.Management.Automation

# 或者使用 plink 风格
Write-Host "Attempting SSH connection..."
'''

# 保存脚本
script_path = r"E:\ai\agent\ssh_ps.ps1"
with open(script_path, 'w', encoding='utf-8') as f:
    f.write(ps_script)

print(f"Script saved to {script_path}")
