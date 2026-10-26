<#
.SYNOPSIS
  安全的一键修复。只做：安装微软运行库、结束「本整合包自己」残留的进程。不改系统设置、不关杀毒、不碰别的程序。
.PARAMETER Item
  doctor 报告里的 id：webview2 | vcredist | port_6185 | port_6199 | port_6099 | port_6188
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)][ValidateSet('webview2', 'vcredist', 'port_6185', 'port_6199', 'port_6099', 'port_6188')][string]$Item,
    [switch]$Json
)
. (Join-Path $PSScriptRoot '_common.ps1')
function Install-Redist {
    [CmdletBinding(SupportsShouldProcess)]
    param([string]$WingetId, [string]$Url)
    $wg = Get-Command winget -ErrorAction SilentlyContinue
    if ($wg) {
        if ($PSCmdlet.ShouldProcess($WingetId, 'winget 安装')) {
            & winget install --id $WingetId -e --silent --accept-package-agreements --accept-source-agreements | Out-Null
            if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq -1978335189) { return @{ ok = $true; msg = "已通过 winget 安装 $WingetId" } }
            return @{ ok = $false; msg = "winget 安装失败（$LASTEXITCODE）。请手动下载：$Url" }
        }
        return @{ ok = $true; msg = "演练：将执行 winget install $WingetId" }
    }
    return @{ ok = $false; msg = "本机没有 winget。请手动下载安装：$Url" }
}

switch -Wildcard ($Item) {
    'webview2' {
        $r = Install-Redist 'Microsoft.EdgeWebView2Runtime' 'https://developer.microsoft.com/microsoft-edge/webview2/'
    }
    'vcredist' {
        $r = Install-Redist 'Microsoft.VCRedist.2015+.x64' 'https://aka.ms/vs/17/release/vc_redist.x64.exe'
    }
    'port_*' {
        $port = [int]($Item -replace 'port_', '')
        if (-not $script:OnWindows) { $r = @{ ok = $false; msg = '只在 Windows 上可用' }; break }
        $conns = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
        if ($conns.Count -eq 0) { $r = @{ ok = $true; msg = "端口 $port 已经空闲" }; break }
        $killed = @(); $others = @()
        foreach ($c in $conns) {
            $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
            if (-not $proc) { continue }
            if ($proc.Path -and $proc.Path.StartsWith($script:Root, [StringComparison]::OrdinalIgnoreCase)) {
                if ($PSCmdlet.ShouldProcess("$($proc.ProcessName) ($($proc.Id))", '结束本整合包残留进程')) {
                    Stop-Process -Id $proc.Id -Force; $killed += $proc.ProcessName
                }
            } else { $others += $proc.ProcessName }
        }
        if ($others.Count) { $r = @{ ok = $false; msg = "端口 $port 被其他程序占用（$($others -join '、')），为安全起见不会自动关闭，请你自己退出它" } }
        else { $r = @{ ok = $true; msg = "已结束本整合包残留进程：$($killed -join '、')" } }
    }
}
$r['item'] = $Item
if ($Json) { Write-Result $r -Json } else { Write-Output $r.msg }
if (-not $r.ok) { exit 1 }
