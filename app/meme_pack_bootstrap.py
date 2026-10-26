"""首次联网时下载默认表情包「DeepSeek 二创」（不随整合包分发图片，因原素材许可未指定）。

图片来源：https://github.com/anka-afk/deepseek-fanart-meme-pack @ v1.0.0
许可：原素材版权归各权利人；本整合包仅在用户本机首次启动时代为从官方仓库拉取。
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone

PACK_ID = "deepseek-fanart-meme-pack"
PACK_NAME = "DeepSeek 二创表情包"
PACK_VERSION = "1.0.0"
PACK_REPO = "anka-afk/deepseek-fanart-meme-pack"
PACK_REF = "v1.0.0"
# 直连 + 常见 GitHub 加速（与 AstrBot / 表情包管理器默认加速一致）
DOWNLOAD_CANDIDATES = [
    f"https://ghfast.top/https://github.com/{PACK_REPO}/archive/refs/tags/{PACK_REF}.zip",
    f"https://gh-proxy.com/https://github.com/{PACK_REPO}/archive/refs/tags/{PACK_REF}.zip",
    f"https://github.com/{PACK_REPO}/archive/refs/tags/{PACK_REF}.zip",
]

_lock = threading.Lock()
_state = {"status": "idle", "msg": "", "progress": 0}  # idle|downloading|ready|error|skipped


def _plugin_data(astrbot_dir: str) -> str:
    return os.path.join(astrbot_dir, "data", "plugin_data", "meme_manager")


def pack_ready(astrbot_dir: str) -> bool:
    memes = os.path.join(_plugin_data(astrbot_dir), "packs", PACK_ID, "memes")
    if not os.path.isdir(memes):
        return False
    # 至少一个类别目录里有图片
    for root, _dirs, files in os.walk(memes):
        if any(f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")) for f in files):
            return True
    return False


def status() -> dict:
    with _lock:
        return dict(_state)


def _set(**kw):
    with _lock:
        _state.update(kw)


def ensure_runtime_scaffold(astrbot_dir: str) -> None:
    """写 registry / selection_rules 骨架（即使图片还没下完，插件也能启动）。"""
    root = _plugin_data(astrbot_dir)
    for sub in ("packs", "backup", "temp"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    notice = os.path.join(root, "PACK_ATTRIBUTION.txt")
    if not os.path.exists(notice):
        with open(notice, "w", encoding="utf-8") as f:
            f.write(
                "默认表情包 DeepSeek 二创（deepseek-fanart-meme-pack）\n"
                f"来源：https://github.com/{PACK_REPO} @ {PACK_REF}\n"
                "维护：anka-afk（Meme Manager 适配）\n"
                "许可：原素材许可未指定，版权归各权利人；本整合包不二次分发图片，\n"
                "仅在你本机首次启动时从官方仓库下载。详见该仓库 LICENSE。\n"
                "官方-pack 标签是 Meme Manager 维护分类，非 DeepSeek 官方背书。\n"
            )
    reg_path = os.path.join(root, "registry.json")
    sel_path = os.path.join(root, "selection_rules.json")
    installed = []
    if os.path.exists(reg_path):
        try:
            installed = json.load(open(reg_path, encoding="utf-8")).get("installed_packs", []) or []
        except Exception:
            installed = []
    ids = {str(p.get("id") or "") for p in installed if isinstance(p, dict)}
    if PACK_ID not in ids and pack_ready(astrbot_dir):
        installed.append({
            "id": PACK_ID, "name": PACK_NAME, "version": PACK_VERSION,
            "enabled": True, "installed_at": datetime.now(timezone.utc).isoformat(),
        })
    # 若图片未就绪，也不写假的 installed，避免插件以为有包
    if not os.path.exists(reg_path) or PACK_ID in {str(p.get("id") or "") for p in installed if isinstance(p, dict)}:
        with open(reg_path, "w", encoding="utf-8") as f:
            json.dump({"schema_version": 1, "installed_packs": installed}, f, ensure_ascii=False, indent=2)
    if not os.path.exists(sel_path) and pack_ready(astrbot_dir):
        with open(sel_path, "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 1,
                "rules": [{"id": "default", "scope": "default", "pack_id": PACK_ID}],
            }, f, ensure_ascii=False, indent=2)
    elif pack_ready(astrbot_dir) and os.path.exists(sel_path):
        try:
            sel = json.load(open(sel_path, encoding="utf-8"))
            rules = sel.get("rules") if isinstance(sel, dict) else None
            if isinstance(rules, list) and not any(
                isinstance(r, dict) and r.get("scope") == "default" and r.get("pack_id") == PACK_ID for r in rules
            ):
                # 把 DeepSeek 包设为默认（插到最前的 default 规则）
                rules = [r for r in rules if not (isinstance(r, dict) and r.get("scope") == "default")]
                rules.insert(0, {"id": "default", "scope": "default", "pack_id": PACK_ID})
                sel["rules"] = rules
                with open(sel_path, "w", encoding="utf-8") as f:
                    json.dump(sel, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def _download(url: str, dest: str, timeout: int = 600) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "QiushiDafeiyuConnector/1.0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total:
                _set(progress=min(99, int(done * 100 / total)), msg=f"下载中 {done // 1024 // 1024}MB/{total // 1024 // 1024}MB")


def _install_from_zip(zip_path: str, astrbot_dir: str) -> None:
    root = _plugin_data(astrbot_dir)
    packs = os.path.join(root, "packs")
    os.makedirs(packs, exist_ok=True)
    target = os.path.join(packs, PACK_ID)
    with tempfile.TemporaryDirectory(prefix="meme_pack_") as tmp:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        # 找到带 manifest.json 且 id 匹配的目录
        pack_src = None
        for dirpath, _dirs, files in os.walk(tmp):
            if "manifest.json" in files:
                try:
                    m = json.load(open(os.path.join(dirpath, "manifest.json"), encoding="utf-8"))
                except Exception:
                    continue
                if str(m.get("id") or "") == PACK_ID:
                    pack_src = dirpath
                    break
        if not pack_src:
            raise RuntimeError("压缩包里找不到 deepseek-fanart-meme-pack 的 manifest.json")
        if os.path.exists(target):
            shutil.rmtree(target)
        shutil.copytree(pack_src, target)
        # 复制上游 LICENSE 到包内（若有）
        for name in ("LICENSE", "README.md"):
            src = os.path.join(pack_src, name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(target, name))
    ensure_runtime_scaffold(astrbot_dir)
    # 强制写入 registry + 默认选包
    reg_path = os.path.join(root, "registry.json")
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "installed_packs": [{
                "id": PACK_ID, "name": PACK_NAME, "version": PACK_VERSION,
                "enabled": True, "installed_at": datetime.now(timezone.utc).isoformat(),
                "source": {"type": "github", "repo": PACK_REPO, "ref": PACK_REF},
            }],
        }, f, ensure_ascii=False, indent=2)
    with open(os.path.join(root, "selection_rules.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "rules": [{"id": "default", "scope": "default", "pack_id": PACK_ID}],
        }, f, ensure_ascii=False, indent=2)


def install_default_pack(astrbot_dir: str, *, force: bool = False) -> dict:
    """同步下载并安装。已就绪则跳过。"""
    ensure_runtime_scaffold(astrbot_dir)
    if pack_ready(astrbot_dir) and not force:
        _set(status="ready", msg="默认表情包已就绪", progress=100)
        return status()
    _set(status="downloading", msg="开始下载 DeepSeek 二创表情包…", progress=0)
    err = None
    with tempfile.TemporaryDirectory(prefix="meme_dl_") as tmp:
        zip_path = os.path.join(tmp, "pack.zip")
        for url in DOWNLOAD_CANDIDATES:
            try:
                _set(msg=f"尝试 {url.split('://',1)[-1][:60]}…")
                _download(url, zip_path)
                _set(msg="解压安装中…", progress=99)
                _install_from_zip(zip_path, astrbot_dir)
                if not pack_ready(astrbot_dir):
                    raise RuntimeError("安装后未发现图片文件")
                _set(status="ready", msg="默认表情包安装完成", progress=100)
                return status()
            except Exception as e:  # noqa: BLE001
                err = e
                continue
    _set(status="error", msg=f"下载失败：{err!r}。可稍后在管理后台「表情包管理器 → 资源广场」手动安装 DeepSeek 二创表情包。", progress=0)
    return status()


def ensure_default_pack_async(astrbot_dir: str) -> None:
    """后台线程：首次启动时拉表情包。可重复调用，有锁。"""
    if pack_ready(astrbot_dir):
        ensure_runtime_scaffold(astrbot_dir)
        _set(status="ready", msg="默认表情包已就绪", progress=100)
        return
    with _lock:
        if _state["status"] == "downloading":
            return

    def run():
        try:
            install_default_pack(astrbot_dir)
        except Exception as e:  # noqa: BLE001
            _set(status="error", msg=repr(e))

    threading.Thread(target=run, name="meme-pack-bootstrap", daemon=True).start()
