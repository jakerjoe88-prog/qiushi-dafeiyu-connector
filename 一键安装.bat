@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\setup.ps1"
if errorlevel 1 (
  echo.
  echo 安装出错，详情见 install.log
)
pause
