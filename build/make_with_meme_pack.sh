#!/usr/bin/env bash
# 可选：从已组装的 dist/QQAI 再生成一份「含表情包」副本（自 v1.0.4 起公开 zip 已默认含图片，通常无需再跑）。
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
if not m.pack_ready(astr):
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

cat > "$OUTDIR/QQAI/【说明】表情包已随公开包预装.txt" << 'TXT'
自 v1.0.4 起，公开 Release 的 QQAI-offline-win64.zip 默认已预装 DeepSeek 二创表情包（据项目方声明作者已授权二次分发）。
本 with-meme-pack 目录仅作可选复刻，一般不必单独使用。
TXT

cd "$OUTDIR"
python3 -c "import shutil;shutil.make_archive('QQAI-offline-win64-with-meme-pack','zip','.','QQAI')"
ls -lah "$OUTDIR"
