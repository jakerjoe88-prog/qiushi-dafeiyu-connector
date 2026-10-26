<#
.SYNOPSIS
  非交互配置：填 DeepSeek API Key、机器人 QQ、（可选）主人 QQ。会先测试 Key 再保存。Key 不会被打印或写进日志。
.EXAMPLE
  .\tools\configure.ps1 -BotQQ 123456789 -AdminQQ 987654321      # Key 从环境变量 DEEPSEEK_API_KEY 读取（推荐）
  .\tools\configure.ps1 -ApiKey sk-xxxx -BotQQ 123456789
#>
[CmdletBinding()]
param(
    [string]$ApiKey = '',
    [Parameter(Mandatory)][ValidatePattern('^[1-9][0-9]{4,11}$')][string]$BotQQ,
    [ValidatePattern('^([1-9][0-9]{4,11})?$')][string]$AdminQQ = '',
    [switch]$SkipTest,
    [switch]$Json
)
. (Join-Path $PSScriptRoot '_common.ps1')
if (-not $ApiKey) { $ApiKey = [string]$env:DEEPSEEK_API_KEY }
$py = Get-PythonExe
$cliArgs = @($script:Launcher, '--configure', '--qq', $BotQQ)
if ($AdminQQ) { $cliArgs += @('--admin', $AdminQQ) }
if ($SkipTest) { $cliArgs += '--skip-test' }
$env:QQAI_API_KEY = $ApiKey.Trim()
try { $out = (& $py @cliArgs 2>&1 | Out-String) } finally { Remove-Item Env:QQAI_API_KEY -ErrorAction SilentlyContinue }
$out = Hide-Secret $out
$line = ($out -split "`n" | Where-Object { $_.Trim().StartsWith('{') } | Select-Object -Last 1)
if (-not $line) { $res = @{ ok = $false; step = 'python'; msg = $out.Trim() } } else { $res = $line | ConvertFrom-Json }
if ($Json) { Write-Result $res -Json }
elseif ($res.ok) { Write-Output "配置成功：$($res.msg)（Key 已保存，显示为 sk-***）" }
else { Write-Output "配置失败（$($res.step)）：$($res.msg)" }
if (-not $res.ok) { exit 2 }
