# 许可与致谢（秋实的大肥鱼连接器）

整合包作者：秋实KL（抖音 @秋实KL）。本整合包**仅限免费分发，禁止商用**。包中自己编写的启动器、脚本和文档同样免费提供。各第三方组件以其原许可为准，**未修改任何上游代码**。

## 1. NapCatQQ —— 有限再分发许可（Limited Redistribution License）
- 版权：Copyright © 2024 Mlikiowa（NapNeko 团队）
- 源码与出处：https://github.com/NapNeko/NapCatQQ
- 本包使用的版本：NapCat.Shell.Windows.Node v4.18.41，原样再分发，未作任何修改。按许可要求，以下附上许可全文（原文见 `licenses/NapCat-LICENSE.txt`）：

```
Limited Redistribution License for NapCat

Copyright © 2024 Mlikiowa

1. Usage and Reproduction:
   - Unauthorized use, reproduction, modification, or distribution of this code is prohibited without explicit permission from the main author of the NapCat repository.
   
2. Redistribution:
   - Redistribution of this code is permitted, provided that the full text of this license is included, and the source and copyright information is clearly stated.
   - Minor modifications and extensions are allowed for redistribution purposes, but the modified code must not be publicly released.

3. Non-Commercial Use:
   - This code is not to be used for any commercial purposes.

4. Additional Permissions:
   - Any rights not explicitly addressed in this license must be requested from and granted by the main author of the NapCat repository.

5. Disclaimer:
   - This code is provided "as is," without any express or implied warranties, including but not limited to the implied warranties of merchantability and fitness for a particular purpose. In no event shall the author be liable for any damages or other liability arising from, out of, or in connection with the use or distribution of this code.
```

## 2. AstrBot —— GNU AGPL-3.0
- 源码：https://github.com/AstrBotDevs/AstrBot （本包使用 tag v4.29.3，原样未修改）
- 许可全文：`licenses/AstrBot-LICENSE-AGPL-3.0.txt`；EULA：`licenses/AstrBot-EULA.md`
- 依据 AGPL-3.0，你可以从上面的地址获取完整的对应源码。本包内的 `runtime/AstrBot` 也是 Python 源码形式。

## 3. astrbot_plugin_group_chat_plus —— GNU AGPL-3.0
- 源码：https://github.com/Him666233/astrbot_plugin_group_chat_plus （本包为 V1.2.3.hotfix.2，原样未修改）
- 许可全文：`licenses/group_chat_plus-LICENSE.txt`

## 4. 表情包管理器 meme_manager —— MIT
- 源码：https://github.com/anka-afk/astrbot_plugin_meme_manager （本包为 v5.2.7，原样未修改）
- 许可全文：`licenses/meme_manager-LICENSE-MIT.txt`
- 依赖（faiss-cpu、pillow、boto3 等）已预装进 `runtime/python/Lib/site-packages`，见第 6 节。

## 5. DeepSeek 二创表情包（公开 Release 默认随 zip 预装图片）
- 上游：https://github.com/anka-afk/deepseek-fanart-meme-pack @ v1.0.0（id `deepseek-fanart-meme-pack`；维护 anka-afk）
- **据项目方声明：作者已授权二次分发**（约 2026-10-26）。公开 GitHub Release zip **默认附带**约 174 张图片，并写入 registry / selection_rules 设为默认。
- 上游原 LICENSE 文件随包保留在 `runtime/AstrBot/data/plugin_data/meme_manager/packs/deepseek-fanart-meme-pack/LICENSE`（原文仍为内容说明 / NOASSERTION 表述）；版权归各权利人。
- 兜底：若本机 packs 目录缺失图片，启动器可后台静默从官方仓库补齐（无下载按钮、无界面进度条）。
- 说明文件：`licenses/DeepSeek二创表情包-来源说明.txt`（用户本机也会有一份）。

## 6. Python 与第三方库
- 嵌入式 CPython 3.12.10：PSF License，见 `licenses/Python-LICENSE.txt`
- 其余 Python 依赖的名称、版本和许可列表见 `licenses/third-party-python-packages.txt`，各自的许可证文本在 `runtime/python/Lib/site-packages/*.dist-info` 中。

## 7. 微软运行库（不随包分发）
本整合包**不附带** Visual C++ Redistributable 或 WebView2 Runtime 安装包。环境检测发现缺失时，`tools/fix.ps1` 会调用本机 `winget` 安装：
- Microsoft.VCRedist.2015+.x64（https://aka.ms/vs/17/release/vc_redist.x64.exe）
- Microsoft.EdgeWebView2Runtime（https://developer.microsoft.com/microsoft-edge/webview2/）
安装时视为你接受微软的许可条款。版权归 Microsoft Corporation 所有。

## 8. 免责声明
QQ 机器人不是腾讯官方功能，使用有封号风险。本整合包按“原样”提供，不附带任何担保。因使用本整合包造成的任何损失，作者和上游项目均不承担责任。
