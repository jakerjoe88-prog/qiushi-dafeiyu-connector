# 公共函数：被 doctor / fix / configure / start / status / stop 点源引用
Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { Write-Verbose '无法设置控制台编码' }
$script:Root    = Split-Path -Parent $PSScriptRoot
$script:Runtime = Join-Path $Root 'runtime'
$script:PyDir   = Join-Path $Runtime 'python'
$script:Py      = Join-Path $PyDir 'python.exe'
$script:PyW     = Join-Path $PyDir 'pythonw.exe'
$script:Launcher = Join-Path $Root 'app\launcher.py'
$script:UiPort  = 6188
$script:OnWindows = ($PSVersionTable.PSVersion.Major -le 5) -or $IsWindows

function Get-PythonExe {
    if (Test-Path $script:Py) { return $script:Py }
    $c = Get-Command python -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    $c = Get-Command python3 -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    throw '找不到整合包自带的 Python（runtime\python\python.exe），整合包可能没有完整解压'
}

function Test-PortListening([int]$Port) {
    $c = New-Object Net.Sockets.TcpClient
    try {
        $iar = $c.BeginConnect('127.0.0.1', $Port, $null, $null)
        if ($iar.AsyncWaitHandle.WaitOne(400)) { $c.EndConnect($iar); return $true }
        return $false
    } catch { return $false } finally { $c.Close() }
}

function Get-UiStatus {
    if (-not (Test-PortListening $script:UiPort)) { return $null }
    try {
        $s = Invoke-RestMethod -Uri "http://127.0.0.1:$($script:UiPort)/api/status" -TimeoutSec 5
        $s.PSObject.Properties.Remove('dashboard_password')
        return $s
    } catch { return $null }
}

function Write-Result($Obj, [switch]$Json) {
    if ($Json) { $Obj | ConvertTo-Json -Depth 6 -Compress | Write-Output }
}

function Hide-Secret([string]$Text) {
    return [regex]::Replace($Text, 'sk-[A-Za-z0-9_\-]{6,}', 'sk-***')
}
