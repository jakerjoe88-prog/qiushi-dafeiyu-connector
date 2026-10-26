#!/usr/bin/env bash
# 从已组装的 dist/QQAI 生成「含表情包图片」的本地自测包（不上传 GitHub Release）。
# 前置：dist/QQAI 已存在；CACHE 内有 deepseek-fanart-meme-pack-v1.0.0.zip
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="${CACHE:-/workspace/offline_cache}"
SRC="$HERE/dist/QQAI"
OUTDIR="$HERE/dist/with-meme-pack"
PACK_ZIP="$CACHE/deepseek-fanart-meme-pack-v1.0.0.zip"

if [[ ! -d "$SRC" ]]; then
  echo "缺少 $SRC，请先跑 build/build_offline.sh" >&2
  exit 1
fi
if [[ ! -f "$PACK_ZIP" ]]; then
  echo "缺少 $PACK_ZIP（先下载官方 tag zip）" >&2
  exit 1
fi

rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"
cp -a "$SRC" "$OUTDIR/QQAI"

python3 - <<PY
import sys
sys.path.insert(0, "$OUTDIR/QQAI/app")
import meme_pack_bootstrap as m
astr = "$OUTDIR/QQAI/runtime/AstrBot"
m.install_from_zip("$PACK_ZIP", astr)
assert m.pack_ready(astr), "pack not ready after install"
import os
memes = os.path.join(astr, "data/plugin_data/meme_manager/packs", m.PACK_ID, "memes")
n = 0
for root, _d, files in os.walk(memes):
    n += sum(1 for f in files if f.lower().endswith((".png",".jpg",".jpeg",".gif",".webp")))
print("installed images:", n)
assert n >= 174, n
PY

# 本地自测说明（仅 with-meme-pack）
cat > "$OUTDIR/QQAI/【本地自测】含表情包图片.txt" << 'TXT'
本目录是作者本地自测包：已预装 DeepSeek 二创表情包 174 张图片。
因上游 LICENSE=NOASSERTION（无再分发授权），此包【不要】上传到公开 GitHub Release。
公开用户请使用 Release 里的 QQAI-offline-win64.zip（首次启动后台静默下载图片）。
TXT

cd "$OUTDIR"
python3 -c "import shutil;shutil.make_archive('QQAI-offline-win64-with-meme-pack','zip','.','QQAI')"
ls -lah "$OUTDIR"
# 确认公开 zip 路径未混入图片包
echo "public zip should remain at dist/QQAI-offline-win64.zip (no images)"
