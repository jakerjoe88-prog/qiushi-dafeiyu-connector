<#
.SYNOPSIS
  秋实的大肥鱼连接器 · 环境检测。输出中文结果，并写入 doctor-report.json（整合包根目录）。
.PARAMETER Json
  只输出一行 JSON（给控制台 / AI 代理解析用）。
.PARAMETER NoNetwork
  跳过 DeepSeek 联网检测。
#>
[CmdletBinding()]
param([switch]$Json, [switch]$NoNetwork)
. (Join-Path $PSScriptRoot '_common.ps1')

$checks = New-Object System.Collections.ArrayList
function Add-Check {
    param([string]$Id, [string]$Name, [ValidateSet('ok', 'warn', 'fail', 'skip')][string]$Status,
          [string]$Detail, [string]$FixHint = '', [bool]$AutoFix = $false)
    [void]$checks.Add([ordered]@{ id = $Id; name = $Name; status = $Status; detail = $Detail;
                                  fix = $FixHint; auto_fix = $AutoFix })
}
function Get-RegValue([string]$Path, [string]$Name) {
    try { return (Get-ItemProperty -Path $Path -Name $Name -ErrorAction Stop).$Name } catch { return $null }
}

# 1 系统版本
if ($script:OnWindows) {
    $build = [Environment]::OSVersion.Version.Build
    if ($build -ge 17763) { Add-Check 'os' '系统版本' 'ok' "Windows 内部版本 $build" }
    else { Add-Check 'os' '系统版本' 'fail' "Windows 内部版本 $build，太旧" '需要 Windows 10 1809 或更新版本（推荐 Windows 11）' }
} else { Add-Check 'os' '系统版本' 'skip' '不是 Windows（仅演练）' }

# 2 架构
if ([Environment]::Is64BitOperatingSystem) { Add-Check 'arch' '64 位系统' 'ok' 'x64' }
else { Add-Check 'arch' '64 位系统' 'fail' '32 位系统' '本整合包只支持 64 位 Windows' }

# 3 WebView2
if ($script:OnWindows) {
    $g = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
    $v = $null
    foreach ($p in @("HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$g",
                     "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$g",
                     "HKCU:\Software\Microsoft\EdgeUpdate\Clients\$g")) {
        $x = Get-RegValue $p 'pv'
        if ($x -and $x -ne '0.0.0.0') { $v = $x; break }
    }
    if ($v) { Add-Check 'webview2' 'WebView2 运行库（控制台窗口）' 'ok' "版本 $v" }
    else { Add-Check 'webview2' 'WebView2 运行库（控制台窗口）' 'warn' '未安装：控制台会改用浏览器打开，功能不受影响' '点「一键修复」安装 Microsoft Edge WebView2 运行库' $true }
} else { Add-Check 'webview2' 'WebView2 运行库（控制台窗口）' 'skip' '不是 Windows' }

# 4 VC++ 运行库
if ($script:OnWindows) {
    $inst = Get-RegValue 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64' 'Installed'
    if (-not $inst) { $inst = Get-RegValue 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64' 'Installed' }
    if ($inst -eq 1) { Add-Check 'vcredist' 'VC++ 2015-2022 运行库' 'ok' '已安装' }
    else { Add-Check 'vcredist' 'VC++ 2015-2022 运行库' 'warn' '未检测到，部分组件可能无法启动' '点「一键修复」安装 Microsoft Visual C++ 运行库（x64）' $true }
} else { Add-Check 'vcredist' 'VC++ 2015-2022 运行库' 'skip' '不是 Windows' }

# 5 整合包完整性（Python / AstrBot / NapCat 自带的 QQ NT 内核）
$miss = @()
foreach ($f in @('runtime\python\python.exe', 'runtime\AstrBot\main.py', 'runtime\napcat\napcat.bat', 'app\launcher.py')) {
    if (-not (Test-Path (Join-Path $script:Root $f))) { $miss += $f }
}
if ($miss.Count -eq 0) { Add-Check 'bundle' '整合包文件' 'ok' 'Python、AstrBot、NapCat 都在' }
else { Add-Check 'bundle' '整合包文件' 'fail' ('缺少：' + ($miss -join '，')) '整合包没解压完整或被杀毒软件删了文件：请重新完整解压（用 7-Zip / Bandizip），并把文件夹加入杀毒软件白名单' }

$napDir = Join-Path $script:Runtime 'napcat'
$qqnt = $null
if (Test-Path $napDir) { $qqnt = Get-ChildItem -Path $napDir -Recurse -Filter 'wrapper.node' -ErrorAction SilentlyContinue | Select-Object -First 1 }
if ($qqnt) { Add-Check 'qqnt' 'QQ NT 内核（NapCat 自带）' 'ok' '已内置，无需另装 QQ' }
else { Add-Check 'qqnt' 'QQ NT 内核（NapCat 自带）' 'fail' '找不到 wrapper.node' '整合包里的 NapCat 不完整，请重新解压；若反复消失，是杀毒软件误删，请加白名单后再解压' }

# 6 端口
$ports = [ordered]@{ '6185' = 'AstrBot 管理后台'; '6199' = 'AstrBot ↔ NapCat 连接'; '6099' = 'NapCat WebUI'; '6188' = '本控制台' }
foreach ($p in $ports.Keys) {
    $id = "port_$p"; $nm = "端口 $p（$($ports[$p])）"
    if (-not (Test-PortListening ([int]$p))) { Add-Check $id $nm 'ok' '空闲'; continue }
    $owner = '未知程序'; $ours = $false
    if ($script:OnWindows) {
        try {
            $conn = Get-NetTCPConnection -LocalPort ([int]$p) -State Listen -ErrorAction Stop | Select-Object -First 1
            $proc = Get-Process -Id $conn.OwningProcess -ErrorAction Stop
            $owner = $proc.ProcessName
            if ($proc.Path -and $proc.Path.StartsWith($script:Root, [StringComparison]::OrdinalIgnoreCase)) { $ours = $true }
        } catch { $owner = '未知程序' }
    }
    if ($ours) { Add-Check $id $nm 'ok' '本整合包正在使用' }
    else { Add-Check $id $nm 'fail' "被其他程序占用：$owner" '关掉占用它的程序（常见：另一份 AstrBot / NapCat / QQ 机器人）。若是本整合包残留进程，点「一键修复」结束它' $true }
}

# 7 磁盘
try {
    $drv = (Get-Item $script:Root).PSDrive
    $freeGB = [math]::Round($drv.Free / 1GB, 1)
    if ($freeGB -ge 2) { Add-Check 'disk' '磁盘空间' 'ok' "剩余 $freeGB GB" }
    else { Add-Check 'disk' '磁盘空间' 'fail' "剩余 $freeGB GB，不足 2 GB" '清理磁盘，或把整合包移到空间更大的盘' }
} catch { Add-Check 'disk' '磁盘空间' 'skip' '无法读取' }

# 8 写入权限
$probe = Join-Path $script:Root ('.write-test-' + [guid]::NewGuid().ToString('N'))
try { Set-Content -Path $probe -Value 'x' -ErrorAction Stop; Remove-Item $probe -Force; Add-Check 'perms' '文件夹写入权限' 'ok' '可写' }
catch { Add-Check 'perms' '文件夹写入权限' 'fail' '无法写入整合包文件夹' '不要放在 C:\Program Files 或桌面同步盘里；移动到 D:\QQAI 这类普通文件夹' }

# 9 路径
$r = $script:Root
$bad = @()
if ($r -match '[^\x00-\x7F]') { $bad += '中文/全角字符' }
if ($r -match ' ') { $bad += '空格' }
if ($r.Length -gt 80) { $bad += '路径过长' }
if ($bad.Count -eq 0) { Add-Check 'path' '安装路径' 'ok' $r }
else { Add-Check 'path' '安装路径' 'warn' ("$r（含" + ($bad -join '、') + '）') 'QQ 内核遇到这类路径容易启动失败：把整个文件夹移到例如 D:\QQAI 再运行' }

# 10 杀毒软件
if ($script:OnWindows) {
    try {
        $mp = Get-MpComputerStatus -ErrorAction Stop
        if ($mp.RealTimeProtectionEnabled) { Add-Check 'av' '杀毒软件' 'warn' 'Windows 安全中心实时保护已开启' '若出现文件被删、启动闪退：在「Windows 安全中心 → 病毒和威胁防护 → 排除项」里添加整合包文件夹（需你本人操作）' }
        else { Add-Check 'av' '杀毒软件' 'ok' '未发现拦截' }
    } catch { Add-Check 'av' '杀毒软件' 'warn' '无法读取（可能装了第三方杀软）' '360 / 火绒 等如果提示拦截，请选择「信任 / 允许」，或把整合包文件夹加入白名单' }
} else { Add-Check 'av' '杀毒软件' 'skip' '不是 Windows' }

# 11 DeepSeek 连通
if ($NoNetwork) { Add-Check 'deepseek' '连接 DeepSeek' 'skip' '已跳过' }
else {
    $okNet = $false
    try {
        $resp = Invoke-WebRequest -Uri 'https://api.deepseek.com/' -Method Head -TimeoutSec 8 -UseBasicParsing -ErrorAction Stop
        $okNet = $true; $null = $resp
    } catch {
        $e = $_.Exception
        if ($e.PSObject.Properties['Response'] -and $e.Response) { $okNet = $true }
    }
    if ($okNet) { Add-Check 'deepseek' '连接 DeepSeek' 'ok' 'api.deepseek.com 可以访问' }
    else { Add-Check 'deepseek' '连接 DeepSeek' 'fail' '访问 api.deepseek.com 失败' '检查网络；如果开着代理/加速器，试试关闭或切到直连；公司/校园网可能拦截，换手机热点测试' }
}

$fails = @($checks | Where-Object { $_.status -eq 'fail' }).Count
$warns = @($checks | Where-Object { $_.status -eq 'warn' }).Count
$report = [ordered]@{
    schema = 'qqai-doctor/1'; ok = ($fails -eq 0); fails = $fails; warns = $warns
    root = $script:Root; time = (Get-Date).ToString('s'); checks = $checks
}
$path = Join-Path $script:Root 'doctor-report.json'
try { [IO.File]::WriteAllText($path, ($report | ConvertTo-Json -Depth 6), (New-Object Text.UTF8Encoding $false)) }
catch { Write-Verbose "无法写入 $path" }

if ($Json) { Write-Result $report -Json; exit 0 }
$mark = @{ ok = '[ 通过 ]'; warn = '[ 注意 ]'; fail = '[ 失败 ]'; skip = '[ 跳过 ]' }
Write-Output '==== 秋实的大肥鱼连接器 · 环境检测 ===='
foreach ($c in $checks) {
    Write-Output ("{0} {1}：{2}" -f $mark[$c.status], $c.name, $c.detail)
    if ($c.status -in 'warn', 'fail' -and $c.fix) {
        $tail = ''
        if ($c.auto_fix) { $tail = "（可自动修复：tools\fix.bat $($c.id)）" }
        Write-Output ("         → {0}{1}" -f $c.fix, $tail)
    }
}
Write-Output ''
if ($fails -eq 0) { Write-Output "结论：可以运行（$warns 项提示）。报告已保存到 doctor-report.json" }
else { Write-Output "结论：有 $fails 项需要处理，按上面的「→」提示修复后再运行。报告已保存到 doctor-report.json" }
exit 0
