#requires -Version 5.1
# 状态检查：AstrBot 是否在监听 6199、NapCat 是否已连上、面板是否可访问
$ErrorActionPreference = 'SilentlyContinue'
function Show([string]$Name, [bool]$Ok, [string]$Hint) {
    if ($Ok) { Write-Host "[ OK ] $Name" -ForegroundColor Green } else { Write-Host "[ ×× ] $Name  -> $Hint" -ForegroundColor Red }
}
$listen = Get-NetTCPConnection -LocalPort 6199 -State Listen
Show 'AstrBot 已启动（端口 6199）' ([bool]$listen) '看 AstrBot 窗口里的报错'
$est = Get-NetTCPConnection -RemotePort 6199 -State Established
Show 'NapCat 已连接 AstrBot' ([bool]$est) '在 NapCat 窗口扫码登录，或等 5 秒自动重连'
$dash = Get-NetTCPConnection -LocalPort 6185 -State Listen
Show 'AstrBot 管理面板 http://127.0.0.1:6185' ([bool]$dash) '面板未就绪，可稍后再看'
$qq = Get-Process -Name QQ
Show 'QQ 进程运行中' ([bool]$qq) 'NapCat 未启动 QQ'
if ($listen -and $est) { Write-Host "`n一切正常：用另一个 QQ 私聊机器人或在群里 @ 它试试吧！" -ForegroundColor Cyan }
