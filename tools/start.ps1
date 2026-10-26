<#
.SYNOPSIS
  后台启动（不弹窗口）：AstrBot + NapCat。等到 AstrBot 就绪后输出状态。需要先 configure.ps1。
.PARAMETER Window
  同时打开图形控制台窗口（给人看）。
#>
[CmdletBinding()]
param([switch]$Window, [int]$TimeoutSec = 120, [switch]$Json)
. (Join-Path $PSScriptRoot '_common.ps1')
if (-not (Test-PortListening $script:UiPort)) {
    $exe = if (Test-Path $script:PyW) { $script:PyW } else { Get-PythonExe }
    $a = @("`"$($script:Launcher)`"")
    if (-not $Window) { $a += '--no-browser' }
    Start-Process -FilePath $exe -ArgumentList $a -WorkingDirectory $script:Root -WindowStyle Hidden | Out-Null
}
$deadline = (Get-Date).AddSeconds($TimeoutSec)
$s = $null
do {
    Start-Sleep -Seconds 2
    $s = Get-UiStatus
    if ($s -and -not $s.configured) { break }
    if ($s -and $s.astrbot -eq 'ok' -and $s.napcat -ne 'off') { break }
} while ((Get-Date) -lt $deadline)
if (-not $s) { $res = @{ ok = $false; msg = '控制台没有启动，查看 logs\launcher.log' } }
elseif (-not $s.configured) { $res = @{ ok = $false; msg = '还没配置，先运行 tools\configure.ps1' } }
else {
    $qr = $null
    if ($s.qr) { $qr = (Get-ChildItem -Path (Join-Path $script:Runtime 'napcat') -Recurse -Filter 'qrcode*.png' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName }
    $res = [ordered]@{ ok = ($s.astrbot -eq 'ok'); astrbot = $s.astrbot; napcat = $s.napcat; connected = $s.connected
                       need_qr_scan = [bool]($s.qr -and -not $s.connected); qr_path = $qr
                       console = "http://127.0.0.1:$($script:UiPort)/" }
}
if ($Json) { Write-Result $res -Json; exit 0 }
if (-not $res.ok) { Write-Output "启动失败：$($res.msg)"; exit 1 }
Write-Output "已启动：AstrBot=$($res.astrbot) NapCat=$($res.napcat) 已连接QQ=$($res.connected)"
if ($res.need_qr_scan) { Write-Output "请用手机 QQ 扫码登录：打开 $($res.console) 或图片 $($res.qr_path)" }
