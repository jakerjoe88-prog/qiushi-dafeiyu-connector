@echo off
chcp 65001 >nul
if "%~1"=="" (echo 用法：fix.bat ^<检测项id^>，例如 fix.bat vcredist & pause & exit /b 1)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix.ps1" -Item %1
pause
