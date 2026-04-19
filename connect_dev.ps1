$serverHost = "106.52.166.109"
$serverUser = "root"
$serverPassword = "010421"

Write-Host "Connecting to $serverUser@$serverHost..."

# 创建进程
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "ssh"
$psi.Arguments = "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "$serverUser@$serverHost", "echo CONNECTED && cd /opt/manim-dev && git branch --show-current && git log --oneline -3"
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi

# 启动进程
$process.Start() | Out-Null

# 等待密码提示
Start-Sleep -Seconds 2

# 发送密码
$process.StandardInput.WriteLine($serverPassword)
$process.StandardInput.Close()

# 读取输出
$output = $process.StandardOutput.ReadToEnd()
$errOutput = $process.StandardError.ReadToEnd()

$process.WaitForExit()

Write-Host "=== OUTPUT ==="
Write-Host $output

if ($errOutput) {
    Write-Host "=== ERROR ==="
    Write-Host $errOutput
}
