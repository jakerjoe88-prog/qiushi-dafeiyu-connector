#!/usr/bin/env bash
# 组装离线整合包：dist/QQAI  ->  dist/QQAI-offline-win64.zip
# 前置：/workspace/offline_cache 内已下载 build/versions.json 里的所有文件（见 README「如何重新打包」）
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="${CACHE:-/workspace/offline_cache}"
OUT="$HERE/dist/QQAI"
rm -rf "$HERE/dist" && mkdir -p "$OUT/runtime" "$OUT/licenses" "$OUT/docs"

# 1) 启动器
# 每次打包都从 mascot-avatar.png 重生成 icon.ico（禁止用 fish-logo）
python3 "$HERE/build/make_icon.py"
cp -r "$HERE/app" "$OUT/app"; rm -rf "$OUT/app/__pycache__"; rm -f "$OUT/app/web/demo-qr.png"
# 主入口：带看板娘图标的 exe（mingw-w64 交叉编译，见 build/stub），任务栏/资源管理器都显示看板娘 logo
"$HERE/build/stub/build.sh"
cp "$HERE/build/stub/launcher.exe" "$OUT/秋实的大肥鱼连接器.exe"
printf '@echo off\r\ncd /d "%%~dp0"\r\necho 调试模式：窗口里会显示启动器日志\r\n"runtime\\python\\python.exe" "app\\launcher.py"\r\npause\r\n' > "$OUT/调试启动（出问题时用）.bat"
# 文件夹图标：desktop.ini（启动器首次运行时会 attrib +h +s desktop.ini、+r 文件夹，使其生效）
printf '[.ShellClassInfo]\r\nIconResource=app\\web\\icon.ico,0\r\nInfoTip=秋实的大肥鱼连接器 · 双击「秋实的大肥鱼连接器.exe」启动\r\n' | iconv -f utf-8 -t utf-16 > "$OUT/desktop.ini"
cp "$HERE/app/web/icon.ico" "$OUT/秋实的大肥鱼连接器.ico"

# 2) 嵌入式 Python + Windows wheels
mkdir -p "$OUT/runtime/python"
python3 -c "import zipfile;zipfile.ZipFile('$CACHE/python-3.12.10-embed-amd64.zip').extractall('$OUT/runtime/python')"
printf 'python312.zip\r\n.\r\nLib\\site-packages\r\n..\\AstrBot\r\nimport site\r\n' > "$OUT/runtime/python/python312._pth"
mkdir -p "$OUT/runtime/python/Lib"
cp -r "$CACHE/sp" "$OUT/runtime/python/Lib/site-packages"
find "$OUT/runtime/python" -name __pycache__ -prune -exec rm -rf {} +

# 3) AstrBot 源码 + WebUI + 预装插件
A="$OUT/runtime/AstrBot"; mkdir -p "$A"
(cd "$CACHE/AstrBot-4.29.3" && cp -r astrbot main.py runtime_bootstrap.py requirements.txt pyproject.toml LICENSE EULA.md "$A/")
mkdir -p "$A/data/plugins"
# 预置拟人人格「小鱼」(xiaoyu) 的初始数据库（需 Linux 版 AstrBot 依赖 venv：$CACHE/linvenv）
"$CACHE/linvenv/bin/python" "$HERE/build/seed/make_db.py" "$CACHE/AstrBot-4.29.3" "$A/data/data_v4.db"
python3 -c "import zipfile;zipfile.ZipFile('$CACHE/dashboard.zip').extractall('$A/data')"
P="$A/data/plugins/astrbot_plugin_group_chat_plus"
cp -r "$CACHE/astrbot_plugin_group_chat_plus-main" "$P"
rm -rf "$P/tests" "$P/.git"* 
echo 'argon2-cffi>=23.1.0' > "$P/requirements.txt"   # 去掉 pytest/hypothesis，避免离线时自动 pip

# 表情包管理器（MIT）+ DeepSeek 二创表情包图片（据项目方声明作者已授权二次分发，约 2026-10-26）
M="$A/data/plugins/meme_manager"
cp -r "$CACHE/astrbot_plugin_meme_manager-main" "$M"
rm -rf "$M/tests" "$M/.github" "$M/.git"*
# 依赖已预装进 site-packages（faiss-cpu/pillow/boto3/tqdm…），清空 requirements 避免离线时 pip
printf '# deps bundled in runtime/python/Lib/site-packages\n' > "$M/requirements.txt"
mkdir -p "$A/data/plugin_data/meme_manager/packs" "$A/data/plugin_data/meme_manager/backup" "$A/data/plugin_data/meme_manager/temp"
PACK_ZIP="$CACHE/deepseek-fanart-meme-pack-v1.0.0.zip"
if [[ ! -f "$PACK_ZIP" ]]; then
  echo "缺少 $PACK_ZIP（公开 zip 默认预装表情包图片）" >&2
  exit 1
fi
python3 - <<PY
import sys
sys.path.insert(0, "$OUT/app")
import meme_pack_bootstrap as m
m.install_from_zip("$PACK_ZIP", "$A")
assert m.pack_ready("$A"), "pack not ready after install"
import os
memes = os.path.join("$A", "data/plugin_data/meme_manager/packs", m.PACK_ID, "memes")
n = 0
for root, _d, files in os.walk(memes):
    n += sum(1 for f in files if f.lower().endswith((".png",".jpg",".jpeg",".gif",".webp")))
print("installed images into public QQAI:", n)
assert n >= 174, n
PY

# 4) NapCat（Node 免安装 QQ 版）
python3 -c "import zipfile;zipfile.ZipFile('$CACHE/NapCat.Shell.Windows.Node.zip').extractall('$OUT/runtime/napcat')"

# 5) 许可证与说明
cp "$CACHE/AstrBot-4.29.3/LICENSE" "$OUT/licenses/AstrBot-LICENSE-AGPL-3.0.txt"
cp "$CACHE/AstrBot-4.29.3/EULA.md" "$OUT/licenses/AstrBot-EULA.md"
cp "$CACHE/astrbot_plugin_group_chat_plus-main/LICENSE" "$OUT/licenses/group_chat_plus-LICENSE.txt"
cp "$CACHE/astrbot_plugin_meme_manager-main/LICENSE" "$OUT/licenses/meme_manager-LICENSE-MIT.txt"
cp "$A/data/plugin_data/meme_manager/PACK_ATTRIBUTION.txt" "$OUT/licenses/DeepSeek二创表情包-来源说明.txt"
cp "$A/data/plugin_data/meme_manager/packs/deepseek-fanart-meme-pack/LICENSE" "$OUT/licenses/DeepSeek二创表情包-LICENSE.txt"
cp "$CACHE/NapCat-LICENSE.txt" "$OUT/licenses/NapCat-LICENSE.txt"
cp "$OUT/runtime/python/LICENSE.txt" "$OUT/licenses/Python-LICENSE.txt"
python3 - "$CACHE/sp" "$OUT/licenses/third-party-python-packages.txt" <<'PY'
import sys,glob,os,email
sp,out=sys.argv[1:]
rows=[]
for m in sorted(glob.glob(os.path.join(sp,"*.dist-info","METADATA"))):
    msg=email.message_from_string(open(m,encoding="utf-8",errors="replace").read())
    lic=msg.get("License-Expression") or (msg.get("License") or "").split("\n")[0][:60] or ",".join(c.split("::")[-1].strip() for c in msg.get_all("Classifier",[]) if c.startswith("License"))
    rows.append(f"{msg['Name']}=={msg['Version']}\t{lic or '见包内 LICENSE'}")
open(out,"w",encoding="utf-8").write("本整合包内置的 Python 第三方库（各自许可证文本见 runtime/python/Lib/site-packages/*.dist-info）\n\n"+"\n".join(rows)+"\n")
PY
cp "$HERE/README.md" "$OUT/使用说明.md"
mkdir -p "$OUT/assets"
cp "$HERE/assets/mascot-avatar.png" "$OUT/assets/"; cp "$HERE/docs/改人格教程.md" "$HERE/docs/推荐插件.md" "$OUT/"; cp "$HERE/LICENSE-NOTICES.md" "$OUT/licenses/README-许可与致谢.md"
[ -d "$HERE/docs/screenshots" ] && cp -r "$HERE/docs/screenshots" "$OUT/docs/"
# 给本地 AI 代理的工具与说明书（方式一：让AI帮我装）
cp -r "$HERE/tools" "$OUT/tools"; rm -f "$OUT/tools/doctor-report.json"
cp "$HERE/agent/AGENTS.md" "$HERE/agent/给AI看的安装说明.md" "$HERE/agent/CLAUDE.md" "$HERE/agent/.cursorrules" "$HERE/agent/复制这句话给你的AI.txt" "$OUT/"
printf '@echo off\r\ncd /d "%%~dp0"\r\ncall tools\\doctor.bat\r\n' > "$OUT/环境检测.bat"
# 运行库不打包：缺 WebView2 / VC++ 时由 tools/fix.ps1 用 winget 在线安装

find "$OUT" -name __pycache__ -not -path "*/site-packages/*" -prune -exec rm -rf {} +
# 6) 打包
cd "$HERE/dist" && python3 -c "import shutil;shutil.make_archive('QQAI-offline-win64','zip','.','QQAI')"
ls -la "$HERE/dist"

# 7) 公开 zip 已默认含表情包图片；with-meme-pack 脚本保留作可选复刻
# "$HERE/build/make_with_meme_pack.sh"
