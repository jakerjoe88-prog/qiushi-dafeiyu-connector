# QQ AI 机器人 一键包（Windows）

让你的 QQ 小号变成会聊天的 AI。只需要 **3 步**，只填 **API Key + QQ 号**。

## 准备
- 一台 Windows 10/11 电脑（64 位），能上网（需要访问 GitHub）
- 一个 **DeepSeek API Key**：到 https://platform.deepseek.com 注册 → 充值几块钱 → 「API Keys」里创建，复制以 `sk-` 开头的那串
- 一个给机器人用的 **QQ 小号**（见下方「防封提醒」）
- 电脑上装好 **电脑版 QQ**（没装的话安装程序会自动打开官网下载页）

## 三步上手
1. **解压并安装**：把压缩包解压到一个**没有中文和空格的路径**（例如 `D:\qqai`），双击 `一键安装.bat`。
2. **填两个信息**：弹出的窗口里粘贴 DeepSeek API Key、填写机器人 QQ 号（管理员 QQ 和机器人名字可不填），点「开始安装」。首次安装会自动下载组件，约 5～15 分钟。
3. **扫码登录**：安装完成后会自动启动，在「NapCat」窗口里会出现二维码，用**机器人那个 QQ 号**的手机 QQ 扫码。看到「检查状态」全部 `OK` 就成功了，用你自己的 QQ 私聊它或在群里 @ 它试试。

以后每次使用：双击桌面上的 **「QQ AI 机器人」** 图标即可（一般不需要再扫码）。
出问题时：双击 `检查状态.bat` 看哪一项是 `××`；安装日志在 `install.log`。
高级设置：浏览器打开 http://127.0.0.1:6185 （AstrBot 管理面板，首次登录按面板提示设置密码）。

## ⚠️ 防封提醒（一定要看）
- 第三方 QQ 机器人**不是腾讯官方支持的用法**，账号有被冻结/封禁的风险，**请勿使用主号**。
- 推荐使用**注册较久（养过一段时间）、实名、正常使用过的小号**；新注册的号最容易被风控。
- 不要让机器人刷屏、加大量群/好友、发广告或违规内容；本包默认已调低回复频率、关闭主动搭话。
- 换电脑/换网络后首次登录更容易触发验证，按 QQ 提示完成即可。

## 费用说明
AI 回复按 DeepSeek 实际用量扣费（本包默认使用便宜的 `deepseek-flash` 非思考模式）。一个普通活跃度的群通常**每天几毛到一两块钱**，以 DeepSeek 官网价格为准：https://api-docs.deepseek.com/zh-cn/quick_start/pricing

## 致谢与许可
本包只是安装脚本，安装时从各项目官方地址下载：
[AstrBot](https://github.com/AstrBotDevs/AstrBot)（AGPL-3.0）、
[NapCatQQ](https://github.com/NapNeko/NapCatQQ)（NapCat 有限再分发许可，**禁止商用**）、
[astrbot_plugin_group_chat_plus](https://github.com/Him666233/astrbot_plugin_group_chat_plus)（AGPL-3.0）。
详见 `LICENSE-NOTICES.md`。本包免费提供，请勿用于商业用途。
