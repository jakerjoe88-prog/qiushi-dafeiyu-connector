<#
.SYNOPSIS
  查看运行状态。-Json 输出一行 JSON：ready=true 表示 QQ 已连上、可以聊天。不含任何密码 / Key。
#>
[CmdletBinding()]
param([switch]$Json)
. (Join-Path $PSScriptRoot '_common.ps1')
$s = Get-UiStatus
if (-not $s) {
    $py = Get-PythonExe
    $line = (& $py $script:Launcher --status-json 2>$null | Select-Object -Last 1)
    $s = $line | ConvertFrom-Json
    $s | Add-Member -NotePropertyName console_running -NotePropertyValue $false -Force
} else {
    $s | Add-Member -NotePropertyName console_running -NotePropertyValue $true -Force
    $s | Add-Member -NotePropertyName ready -NotePropertyValue ([bool]$s.connected) -Force
}
$s | Add-Member -NotePropertyName ports -NotePropertyValue ([ordered]@{
        '6185' = (Test-PortListening 6185); '6199' = (Test-PortListening 6199); '6099' = (Test-PortListening 6099) }) -Force
if ($Json) { Write-Result $s -Json; exit 0 }
Write-Output ("已配置：{0}  控制台：{1}  AstrBot：{2}  NapCat：{3}  QQ 已连接：{4}" -f $s.configured, $s.console_running, $s.astrbot, $s.napcat, $s.connected)
if ($s.qr -and -not $s.connected) { Write-Output '等待扫码：打开 http://127.0.0.1:6188/ 用手机 QQ 扫码' }
