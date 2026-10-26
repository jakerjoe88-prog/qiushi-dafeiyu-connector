#!/usr/bin/env bash
# 用 headless Chrome 渲染启动器各界面的演示截图（?demo=...）
OUT="${OUT:-docs/screenshots}"; BASE="${BASE:-http://127.0.0.1:6188/}"
shot(){ google-chrome --headless=new --no-sandbox --hide-scrollbars --force-device-scale-factor=1 --window-size=1180,${3:-800} \
  --virtual-time-budget=4000 --screenshot="$OUT/$2.png" "$BASE?demo=$1${4:+&theme=$4}" >/dev/null 2>&1; }
for s in welcome step1 step1load step1ok step1bad step1err step2 step2err step2same step3 step3ok panel panelpw panelqr panelstart paneloff; do shot $s $s; done
