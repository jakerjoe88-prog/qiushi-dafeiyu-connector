#!/usr/bin/env bash
# 在 Linux 上用 mingw-w64 交叉编译带图标的启动器 exe（apt install mingw-w64）
set -euo pipefail; cd "$(dirname "$0")"
x86_64-w64-mingw32-windres -c 65001 launcher.rc -O coff -o launcher.res
x86_64-w64-mingw32-gcc -municode -mwindows -Os -s launcher.c launcher.res -lshlwapi -o launcher.exe
rm -f launcher.res
