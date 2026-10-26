# 给 AI 代理的安装运行手册 · 秋实的大肥鱼连接器

> 读者：WorkBuddy、豆包、Cursor、Codex、Claude Code、Trae 等本地 AI 代理。
> 目标：在这台 Windows 电脑上，让 QQ 机器人（AstrBot + NapCat + DeepSeek）跑起来。
> 照着下面的步骤**按顺序**做，每一步都有「成功标志」。不要跳步，不要自由发挥。

## 0. 铁律（必须遵守）

1. **只能问人三件事**：DeepSeek API Key、机器人 QQ 号、用手机 QQ 扫码。其他事情你自己按本手册做；本手册没写的，就停下来告诉人，不要猜。
2. **绝不打印、回显、记录、提交 API Key**。不要 `echo` 它，不要写进任何文件、命令历史、聊天回复或 git。传 Key 只用环境变量 `DEEPSEEK_API_KEY`（见第 3 步）。在回复里提到 Key 时，一律写成 `sk-***`。
3. **不修改上游代码**：`runtime\` 目录（AstrBot、NapCat、Python）里的任何文件都不要改。只使用 `tools\` 下的脚本。
4. **不开放公网端口**：不要改监听地址，不要开防火墙规则，不要做端口转发 / 内网穿透。所有服务只在 `127.0.0.1` 上。
5. **不发任何 QQ 消息**，不替人登录别人的账号，不关闭杀毒软件（只能提示人自己加白名单）。
6. 所有命令都在**整合包根目录**（本文件所在的文件夹）里执行，用 PowerShell：
   `powershell -NoProfile -ExecutionPolicy Bypass -File tools\<脚本>.ps1 <参数>`
   下文简写为 `tools\xxx.ps1`。所有脚本都支持 `-Json`，输出一行 JSON，请用 JSON 判断结果。

## 1. 环境检测

```
tools\doctor.ps1 -Json
```

- 成功标志：JSON 里 `"ok": true`（允许有 `warn`）。报告同时保存在 `doctor-report.json`（格式见 `tools\doctor-report.schema.json`）。
- 如果 `ok` 是 `false`：对每个 `status` 为 `fail` 的项：
  - `auto_fix` 为 `true` → 运行 `tools\fix.ps1 -Item <id> -Json`，然后重新跑第 1 步。
  - `auto_fix` 为 `false` → 把该项的 `fix` 文字原样告诉人，等人处理好再重跑第 1 步。
- `status` 为 `warn` 且 `auto_fix` 为 `true` 的（如 `webview2`、`vcredist`），也建议修复一次。
- 同一项修复两次仍失败 → 停下，把 `name`、`detail`、`fix` 告诉人。

## 2. 向人要信息

只问这两个问题（一次问完）：

1. 「请把你的 DeepSeek API Key 发给我（在 https://platform.deepseek.com/api_keys 创建，以 sk- 开头）。」
2. 「机器人要登录哪个 QQ 号？（建议用小号）可选：你自己的 QQ 号（作为主人/管理员）。」

## 3. 写入配置

用环境变量传 Key（不要把 Key 写在命令行参数里）：

```
$env:DEEPSEEK_API_KEY = '<人给的 Key>'
tools\configure.ps1 -BotQQ <机器人QQ> [-AdminQQ <主人QQ>] -Json
Remove-Item Env:DEEPSEEK_API_KEY
```

- 成功标志：`"ok": true`。脚本会先真实测试 Key，再保存。
- 失败时看 `step` 和 `msg`：

| step | 含义 | 处理 |
|---|---|---|
| `test_key` + 「格式不对」 | Key 抄错了 | 请人重新复制完整的 Key |
| `test_key` + 「Key 无效 / 401」 | Key 错或已删除 | 请人在 DeepSeek 平台新建一个 |
| `test_key` + 「余额不足 / 402」 | 没钱了 | 请人去 DeepSeek 平台充值（几块钱就够用很久） |
| `test_key` + 「连不上 / 超时」 | 网络问题 | 请人关代理或换网络，重跑第 1 步的 deepseek 项 |
| `api_key` | 没给 Key | 回到第 2 步 |
| `save` | QQ 号格式错等 | 按 `msg` 修正后重试 |

## 4. 启动

```
tools\start.ps1 -Json
```

- 成功标志：`"ok": true` 且 `astrbot` 为 `"ok"`。
- 如果 `need_qr_scan` 为 `true`：告诉人「请用手机 QQ 扫码登录机器人账号」，并让人打开 `console`（http://127.0.0.1:6188/）上的二维码，或打开 `qr_path` 这张图片。**扫码只能由人完成。**
- 失败：运行 `tools\status.ps1 -Json` 并查看 `logs\launcher.log` 的最后 50 行（日志里 Key 已打码），对照第 6 节。

## 5. 确认在线

每 5 秒运行一次 `tools\status.ps1 -Json`，最多 3 分钟：

- 成功标志：`"ready": true`（QQ 已连上 AstrBot）。到这里就完成了，告诉人：
  「装好了。在 QQ 群里 @机器人 或私聊它就能聊天。图形控制台：双击桌面『秋实的大肥鱼连接器』。」
- 3 分钟仍是 `false`：二维码可能过期，运行 `tools\stop.ps1 -Json`，再回到第 4 步（最多重试 2 次）。

## 6. 常见错误与修复

| 现象 | 处理 |
|---|---|
| doctor：`port_XXXX` 被占用 | `auto_fix` 只会结束本整合包残留的进程；若是别的程序，请人自己关掉它 |
| doctor：`path` 含中文/空格 | 请人把整个文件夹移到 `D:\QQAI` 之类的路径，然后从第 1 步重来 |
| doctor：`bundle` / `qqnt` 失败 | 整合包不完整或被杀软删除：请人加白名单后重新完整解压 |
| doctor：`perms` 失败 | 不要放在 `C:\Program Files`；移到普通文件夹 |
| 扫码后提示「登录失败 / 风控」 | 请人在手机 QQ 上确认登录，或换个号；不要反复重试超过 3 次 |
| `ready` 一直 false 但 napcat 为 ok | 运行 `tools\stop.ps1`，再 `tools\start.ps1` |
| PowerShell 提示「禁止运行脚本」 | 命令里要带 `-ExecutionPolicy Bypass`（见第 0 节第 6 条），不要改系统策略 |

## 7. 其他命令

- 停止：`tools\stop.ps1 -Json`
- 打开图形控制台：`tools\start.ps1 -Window`
- AstrBot 管理后台、NapCat WebUI：在图形控制台的「控制台」页点对应按钮打开（密码会自动生成并显示在那里，不要去改）。
- 改人格：AstrBot 管理后台左侧「扩展功能」→「人格设定」→「创建人格」，填「人格 ID」和「系统提示词」后保存；再到左侧「配置文件」→「人格」→「默认采用的人格」选中它并保存。详见 改人格教程.md。菜单名以 AstrBot v4.29.3 dashboard/src/i18n/locales/zh-CN 为准。

## 8. 禁止事项（再次强调）

不打印 Key · 不改 `runtime\` · 不开公网端口 / 防火墙 · 不发 QQ 消息 · 不关杀毒 · 不执行本手册以外的安装命令。
