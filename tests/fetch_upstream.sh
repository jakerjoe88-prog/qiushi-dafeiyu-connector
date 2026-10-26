#!/usr/bin/env bash
# 拉取上游真实默认配置/Schema 供单元测试使用（版本与 core/versions.json 对齐）
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p upstream && cd upstream
tag=$(python3 -c "import json;print(json.load(open('../../core/versions.json'))['astrbot_tag'])")
[ -d astrbot ] || { curl -fsSL "https://codeload.github.com/AstrBotDevs/AstrBot/tar.gz/refs/tags/$tag" -o a.tgz && mkdir astrbot && tar xzf a.tgz -C astrbot --strip-components=1 && rm a.tgz; }
[ -f _conf_schema.json ] || curl -fsSL https://raw.githubusercontent.com/Him666233/astrbot_plugin_group_chat_plus/main/_conf_schema.json -o _conf_schema.json
[ -f napcat_onebot_config.ts ] || curl -fsSL https://raw.githubusercontent.com/NapNeko/NapCatQQ/main/packages/napcat-onebot/config/config.ts -o napcat_onebot_config.ts
if command -v npm >/dev/null && [ ! -d node_modules/@sinclair/typebox ]; then [ -f package.json ] || echo "{\"private\":true}" > package.json; npm i --silent @sinclair/typebox esbuild >/dev/null || echo "npm failed, napcat schema test will skip"; fi
echo ok
