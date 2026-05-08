# GitHub SSH Push Workflow

目标：

- 为当前仓库提供稳定的远程推送方式
- 避开 `HTTPS 443` 波动导致的 `git push` / `git fetch` 失败
- 固化当前已经验证通过的 SSH remote 约定

## 当前约定

- 默认远程：`origin`
- 默认协议：SSH
- 默认地址：`git@github.com:mingze-great/manim.git`
- HTTPS 备用远程：`origin-https`
- HTTPS 备用地址：`https://github.com/mingze-great/manim.git`

当前仓库推荐保持如下状态：

```bash
git remote -v
```

预期：

```text
origin       git@github.com:mingze-great/manim.git (fetch)
origin       git@github.com:mingze-great/manim.git (push)
origin-https https://github.com/mingze-great/manim.git (fetch)
origin-https https://github.com/mingze-great/manim.git (push)
```

## 为什么默认走 SSH

- 这台机器到 `github.com:443` 曾多次出现超时、连接重置、TLS 中断
- 这台机器到 `github.com:22` 可达且已验证可认证
- SSH 方式更适合长期频繁 `push/fetch`

## 当前已验证通过的 key

- 私钥：`C:\Users\Administrator\.ssh\id_ed25519_github_manim`
- 公钥注释：`administrator@DESKTOP-UF3585C-github`
- 指纹：`SHA256:9ljum7SbGL2cGLMFF2vJYq47CoorrqpSqvPVQKUEqRU`

## 当前 SSH 配置

文件：`C:\Users\Administrator\.ssh\config`

应包含：

```sshconfig
Host github.com
    HostName github.com
    User git
    IdentityFile C:\Users\Administrator\.ssh\id_ed25519_github_manim
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
    ConnectTimeout 30
```

## 首次验证

```bash
ssh -T git@github.com
```

预期输出：

```text
Hi mingze-great! You've successfully authenticated, but GitHub does not provide shell access.
```

## 日常推送流程

### 1. 检查当前状态

```bash
git status -sb
```

### 2. 推送当前分支

例如当前开发分支：

```bash
git push origin feature/stickman-v2-viral-hook-optimization-acceptance
```

如果当前就在目标分支，也可以直接：

```bash
git push origin HEAD
```

### 3. 验证远端分支头

```bash
git ls-remote origin refs/heads/feature/stickman-v2-viral-hook-optimization-acceptance
git rev-parse HEAD
```

预期：

- 两个提交 SHA 一致

## 日常拉取流程

```bash
git fetch origin
git status -sb
```

如果只更新某个分支：

```bash
git fetch origin repro/3002-12fbd6a6
```

## 为当前 3002 发布 repro 分支

示例：

```bash
git push origin 12fbd6a6e2b1efeea9398421b8205e05af367f32:refs/heads/repro/3002-12fbd6a6
```

## 新机器或新 key 的处理

### 1. 生成新 key

Windows `cmd`：

```cmd
"%WINDIR%\System32\OpenSSH\ssh-keygen.exe" -t ed25519 -C administrator@DESKTOP-UF3585C-github -f "%USERPROFILE%\.ssh\id_ed25519_github_manim" -N ""
```

### 2. 读取公钥

```bash
Get-Content -LiteralPath "$HOME\.ssh\id_ed25519_github_manim.pub"
```

### 3. 加到 GitHub

- GitHub `Settings`
- `SSH and GPG keys`
- `New SSH key`
- 粘贴 `.pub` 全内容

### 4. 验证

```bash
ssh -T git@github.com
```

### 5. 切换 remote

```bash
git remote add origin-https https://github.com/mingze-great/manim.git
git remote set-url origin git@github.com:mingze-great/manim.git
```

如果 `origin-https` 已存在，只执行第二条即可。

## HTTPS 备用回退

如果某些环境只能走 HTTPS：

```bash
git remote set-url origin https://github.com/mingze-great/manim.git
```

或者直接使用备用 remote：

```bash
git fetch origin-https
git push origin-https HEAD:feature/stickman-v2-viral-hook-optimization-acceptance
```

注意：

- 当前这台机器不推荐把 HTTPS 作为默认 remote
- 仅在 SSH 临时不可用时作为备用手段

## 常见故障

### 1. `Permission denied (publickey)`

优先检查：

- `C:\Users\Administrator\.ssh\config` 是否指向正确 key
- 公钥是否已加到正确的 GitHub 账号
- 当前账号是否有仓库写权限
- `ssh -T git@github.com` 返回的用户名是否正确

### 2. `git push` 仍走 HTTPS

检查：

```bash
git remote -v
```

如果 `origin` 不是 `git@github.com:...`，重新设置：

```bash
git remote set-url origin git@github.com:mingze-great/manim.git
```

### 3. 新 key 无法认证

检查：

```bash
ssh-keygen -lf "$HOME\.ssh\id_ed25519_github_manim.pub"
ssh -vvv -T git@github.com
```

重点确认：

- 指纹是否与 GitHub 页面一致
- `IdentityFile` 是否命中新 key

## 关联文档

- `docs/REPRO_3002_FROM_REMOTE.md`
- `docs/V2_3002_STANDARD_DEPLOY.md`
