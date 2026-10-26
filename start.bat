@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "runtime\bot_qq.txt" (
  echo 还没安装，请先双击“一键安装.bat”
  pause
  exit /b 1
)
set /p BOTQQ=<runtime\bot_qq.txt
echo 启动 AstrBot ...
start "AstrBot（别关）" /D "%~dp0runtime\AstrBot" "%~dp0runtime\venv\Scripts\python.exe" main.py
timeout /t 8 /nobreak >nul
echo 启动 NapCat（QQ %BOTQQ%）... 首次需要用手机 QQ 扫码
start "NapCat（别关，在这里扫码）" /D "%~dp0runtime\napcat" cmd /c launcher-user.bat -q %BOTQQ%
timeout /t 25 /nobreak >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\status.ps1"
echo.
echo 若显示 ×× ，过半分钟双击“检查状态.bat”再看。本窗口可关闭。
pause
