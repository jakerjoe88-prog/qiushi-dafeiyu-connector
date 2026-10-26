@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0doctor.ps1" %*
if /i not "%~1"=="-Json" pause
