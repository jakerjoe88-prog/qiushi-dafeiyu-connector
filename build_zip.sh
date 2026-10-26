#!/usr/bin/env bash
# 打包发行 zip：只包含本项目脚本，不含任何上游二进制（安装时再下载）
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pytest -q tests
out=dist/qq-ai-oneclick.zip
mkdir -p dist && rm -f "$out"
# Windows 的 bat/ps1 需要 CRLF；ps1 加 UTF-8 BOM 以兼容 PowerShell 5.1 中文
stage=$(mktemp -d)/qq-ai-oneclick
mkdir -p "$stage"
cp -r core installer README.md LICENSE-NOTICES.md start.bat 一键安装.bat 检查状态.bat "$stage/"
find "$stage" \( -name '*.bat' -o -name '*.ps1' \) -print0 | while IFS= read -r -d '' f; do
  sed -i 's/\r$//; s/$/\r/' "$f"
done
find "$stage" -name '*.ps1' -print0 | while IFS= read -r -d '' f; do
  printf '\xEF\xBB\xBF' | cat - "$f" > "$f.bom" && mv "$f.bom" "$f"
done
find "$stage" -name '__pycache__' -prune -exec rm -rf {} +
python3 -c "import shutil,sys; shutil.make_archive(sys.argv[1], 'zip', sys.argv[2], 'qq-ai-oneclick')" "${out%.zip}" "$(dirname "$stage")"
echo "built $out"
