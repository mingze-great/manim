# Install gh CLI if not installed
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Installing GitHub CLI..."
    winget install GitHub.cli -s winget --silent --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# Authenticate gh
gh auth status || gh auth login

# Add SSH key as secret
$sshKey = Get-Content "C:\Users\Administrator\.ssh\id_rsa" -Raw
gh secret set SERVER_SSH_KEY --body $sshKey --repo mingze-great/manim

Write-Host "SSH key added to GitHub Secrets!"
