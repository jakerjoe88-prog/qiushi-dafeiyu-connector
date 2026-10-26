#requires -Version 5.1
<#
  QQ AI 一键包 安装向导
  - 弹出窗口填写 DeepSeek API Key + 机器人 QQ 号（可选：管理员 QQ、人格名）
  - 安装时从上游官方地址下载 uv / Python / AstrBot / NapCat / 插件（本包不含任何上游二进制）
  - 生成全部配置，创建桌面快捷方式
#>
[CmdletBinding()]
param(
    [string]$ApiKey,
    [string]$QQ,
    [string]$AdminQQ = '',
    [string]$Persona = '小助手',
    [switch]$NoGui
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root = Split-Path -Parent $PSScriptRoot
$Rt = Join-Path $Root 'runtime'
$Dl = Join-Path $Rt 'downloads'
$AstrDir = Join-Path $Rt 'AstrBot'
$NapDir = Join-Path $Rt 'napcat'
$Versions = Get-Content -Raw -Encoding UTF8 (Join-Path $Root 'core\versions.json') | ConvertFrom-Json
$LogFile = Join-Path $Root 'install.log'

function Write-InstallLog([string]$Msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $Msg
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Get-UserInput {
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing
    $f = New-Object Windows.Forms.Form
    $f.Text = 'QQ AI 一键包 - 设置'; $f.Size = New-Object Drawing.Size(460, 330)
    $f.StartPosition = 'CenterScreen'; $f.FormBorderStyle = 'FixedDialog'; $f.MaximizeBox = $false
    $f.Font = New-Object Drawing.Font('Microsoft YaHei UI', 9)
    $labels = @('DeepSeek API Key（必填）', '机器人 QQ 号（必填）', '管理员 QQ 号（可选，填你自己的大号）', '机器人名字（可选）')
    $boxes = @()
    for ($i = 0; $i -lt 4; $i++) {
        $l = New-Object Windows.Forms.Label
        $l.Text = $labels[$i]; $l.Location = New-Object Drawing.Point(20, (20 + $i * 55)); $l.AutoSize = $true
        $t = New-Object Windows.Forms.TextBox
        $t.Location = New-Object Drawing.Point(20, (40 + $i * 55)); $t.Width = 400
        $f.Controls.AddRange(@($l, $t)); $boxes += $t
    }
    $boxes[0].UseSystemPasswordChar = $true
    $boxes[3].Text = '小助手'
    $ok = New-Object Windows.Forms.Button
    $ok.Text = '开始安装'; $ok.Location = New-Object Drawing.Point(320, 245); $ok.Width = 100
    $ok.DialogResult = [Windows.Forms.DialogResult]::OK
    $f.AcceptButton = $ok; $f.Controls.Add($ok)
    while ($true) {
        if ($f.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) { exit 1 }
        $k = $boxes[0].Text.Trim(); $q = $boxes[1].Text.Trim(); $a = $boxes[2].Text.Trim()
        if ($k -notmatch '^sk-.{16,}$') { [Windows.Forms.MessageBox]::Show('API Key 应以 sk- 开头，请检查。') | Out-Null; continue }
        if ($q -notmatch '^[1-9]\d{4,11}$') { [Windows.Forms.MessageBox]::Show('QQ 号应为 5-12 位数字。') | Out-Null; continue }
        if ($a -and $a -notmatch '^[1-9]\d{4,11}$') { [Windows.Forms.MessageBox]::Show('管理员 QQ 号格式不对。') | Out-Null; continue }
        return @{ ApiKey = $k; QQ = $q; AdminQQ = $a; Persona = $(if ($boxes[3].Text.Trim()) { $boxes[3].Text.Trim() } else { '小助手' }) }
    }
}

function Get-File([string]$Url, [string]$Out) {
    if (Test-Path $Out) { Write-InstallLog "已存在，跳过下载: $Out"; return }
    Write-InstallLog "下载 $Url"
    for ($i = 1; $i -le 3; $i++) {
        try { Invoke-WebRequest -Uri $Url -OutFile "$Out.part" -UseBasicParsing; Move-Item "$Out.part" $Out -Force; return }
        catch { Write-InstallLog "下载失败（第 $i 次）: $($_.Exception.Message)"; Start-Sleep -Seconds 3 }
    }
    throw "下载失败: $Url （可能需要科学上网或稍后重试）"
}

function Expand-Single([string]$Zip, [string]$Dest) {
    # 解压后若只有一个顶层目录，则把它的内容提升到 $Dest
    $tmp = "$Dest.tmp"
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    Expand-Archive -Path $Zip -DestinationPath $tmp -Force
    $items = @(Get-ChildItem $tmp)
    $src = if ($items.Count -eq 1 -and $items[0].PSIsContainer) { $items[0].FullName } else { $tmp }
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    Copy-Item -Path (Join-Path $src '*') -Destination $Dest -Recurse -Force
    Remove-Item $tmp -Recurse -Force
}

function Test-QQInstalled {
    $k = 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\QQ'
    return (Test-Path $k)
}

# ---------- 1. 收集输入 ----------
if (-not $NoGui -and -not ($ApiKey -and $QQ)) {
    $in = Get-UserInput
    $ApiKey = $in.ApiKey; $QQ = $in.QQ; $AdminQQ = $in.AdminQQ; $Persona = $in.Persona
}
New-Item -ItemType Directory -Force -Path $Dl | Out-Null
Write-InstallLog "开始安装，机器人 QQ: $QQ"

# ---------- 2. QQ 本体（NapCat 依赖官方 QQNT） ----------
if (-not (Test-QQInstalled)) {
    Write-InstallLog '未检测到电脑版 QQ，打开官方下载页，请安装后再继续'
    Start-Process $Versions.qq_download_page
    Add-Type -AssemblyName System.Windows.Forms
    [Windows.Forms.MessageBox]::Show("请先在打开的网页里下载并安装【电脑版 QQ】，装好后点「确定」继续。") | Out-Null
    if (-not (Test-QQInstalled)) { throw '仍未检测到 QQ，请安装电脑版 QQ 后重新运行「一键安装.bat」' }
}

# ---------- 3. 下载上游组件 ----------
$uvZip = Join-Path $Dl 'uv.zip'; Get-File $Versions.uv_zip $uvZip
$uvDir = Join-Path $Rt 'uv'; if (-not (Test-Path (Join-Path $uvDir 'uv.exe'))) { Expand-Archive $uvZip $uvDir -Force }
$uv = Join-Path $uvDir 'uv.exe'

$astrZip = Join-Path $Dl 'astrbot.zip'; Get-File $Versions.astrbot_src $astrZip
if (-not (Test-Path (Join-Path $AstrDir 'main.py'))) { Expand-Single $astrZip $AstrDir }
$dashZip = Join-Path $Dl 'dashboard.zip'
try { Get-File $Versions.astrbot_dashboard $dashZip; Expand-Archive $dashZip (Join-Path $AstrDir 'data') -Force }
catch { Write-InstallLog "面板下载失败（AstrBot 启动时会自动再下载）: $($_.Exception.Message)" }

$napZip = Join-Path $Dl 'napcat.zip'; Get-File $Versions.napcat_shell $napZip
if (-not (Test-Path (Join-Path $NapDir 'napcat.mjs'))) { Expand-Single $napZip $NapDir }

$plugZip = Join-Path $Dl 'plugin.zip'; Get-File $Versions.plugin_zip $plugZip
$plugDir = Join-Path $AstrDir 'data\plugins\astrbot_plugin_group_chat_plus'
if (-not (Test-Path (Join-Path $plugDir 'main.py'))) { Expand-Single $plugZip $plugDir }

# ---------- 4. Python 环境 ----------
$env:UV_PYTHON_INSTALL_DIR = Join-Path $Rt 'python'
$env:UV_CACHE_DIR = Join-Path $Rt 'uv-cache'
$venv = Join-Path $Rt 'venv'
$py = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $py)) {
    Write-InstallLog '安装 Python（uv 自动下载）'
    & $uv venv --python $Versions.python_version $venv
    if ($LASTEXITCODE) { throw 'Python 环境创建失败' }
}
Write-InstallLog '安装 AstrBot 依赖（首次约 3-10 分钟）'
& $uv pip install --python $py -r (Join-Path $AstrDir 'requirements.txt') aiohttp
if ($LASTEXITCODE) { throw 'AstrBot 依赖安装失败，请检查网络后重试' }
$plugReq = Join-Path $plugDir 'requirements.txt'
if (Test-Path $plugReq) { & $uv pip install --python $py -r $plugReq; if ($LASTEXITCODE) { Write-InstallLog '插件依赖安装有警告' } }

# ---------- 5. 生成配置 ----------
Write-InstallLog '生成配置'
& $py (Join-Path $Root 'core\gen_config.py') --api-key $ApiKey --qq $QQ --admin-qq $AdminQQ --persona $Persona --astrbot-dir $AstrDir --napcat-dir $NapDir
if ($LASTEXITCODE) { throw '配置生成失败' }
& $py (Join-Path $Root 'core\seed_persona.py') $AstrDir
if ($LASTEXITCODE) { Write-InstallLog '人格写入失败（不影响聊天，会使用默认人格）' }
Set-Content -Path (Join-Path $Rt 'bot_qq.txt') -Value $QQ -Encoding ASCII

# ---------- 6. 桌面快捷方式 ----------
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'QQ AI 机器人.lnk'))
$lnk.TargetPath = Join-Path $Root 'start.bat'; $lnk.WorkingDirectory = $Root; $lnk.Save()

Write-InstallLog '安装完成！即将启动机器人。'
Start-Process -FilePath (Join-Path $Root 'start.bat') -WorkingDirectory $Root
