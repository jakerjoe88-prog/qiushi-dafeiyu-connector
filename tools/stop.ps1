<#
.SYNOPSIS
  停止机器人并退出控制台。只结束本整合包目录里的进程。
#>
[CmdletBinding(SupportsShouldProcess)]
param([switch]$Json)
. (Join-Path $PSScriptRoot '_common.ps1')
if (Test-PortListening $script:UiPort) {
    try { Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$($script:UiPort)/api/quit" -Body '{}' -ContentType 'application/json' -TimeoutSec 20 | Out-Null } catch { Write-Verbose '控制台已关闭连接' }
    Start-Sleep -Seconds 3
}
$left = @()
if ($script:OnWindows) {
    $left = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($script:Root, [StringComparison]::OrdinalIgnoreCase) })
    foreach ($p in $left) { if ($PSCmdlet.ShouldProcess("$($p.ProcessName) ($($p.Id))", '结束')) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } }
}
$res = @{ ok = $true; msg = '已停止'; killed_leftovers = $left.Count }
if ($Json) { Write-Result $res -Json } else { Write-Output "已停止（清理残留进程 $($left.Count) 个）" }
