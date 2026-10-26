"""默认表情包「DeepSeek 二创」：公开整合包预装图片；缺失时静默联网补齐。

图片来源：https://github.com/anka-afk/deepseek-fanart-meme-pack @ v1.0.0
据项目方声明（约 2026-10-26）：作者已授权二次分发；上游 LICENSE 原文仍保留在
packs/.../LICENSE。公开 Release zip 默认随包附带 174 张图片并写入 registry/默认规则；
若安装目录缺失图片，启动器仍可后台静默从官方仓库拉取作为兜底（无下载按钮/进度条）。
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
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
# 仅内部状态；启动器 UI 不展示进度/按钮
_state = {"status": "idle", "msg": "", "progress": 0}  # idle|downloading|ready|error|skipped


def _plugin_data(astrbot_dir: str) -> str:
    return os.path.join(astrbot_dir, "data", "plugin_data", "meme_manager")


def pack_ready(astrbot_dir: str) -> bool:
    memes = os.path.join(_plugin_data(astrbot_dir), "packs", PACK_ID, "memes")
    if not os.path.isdir(memes):
        return False
    for _root, _dirs, files in os.walk(memes):
        if any(f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")) for f in files):
            return True
    return False


def status() -> dict:
    with _lock:
        return dict(_state)


def _set(**kw):
    with _lock:
        _state.update(kw)


def _attribution_text() -> str:
    return (
        "默认表情包 DeepSeek 二创（deepseek-fanart-meme-pack）\n"
        f"来源：https://github.com/{PACK_REPO} @ {PACK_REF}\n"
        "维护：anka-afk（Meme Manager 适配）\n"
        "据项目方声明：作者已授权二次分发（约 2026-10-26）。\n"
        "上游 LICENSE 原文随包保留（packs/.../LICENSE）；版权归各权利人。\n"
        "公开整合包默认已预装图片并设为默认；若本机缺失，启动器可后台静默从官方仓库补齐。\n"
        "官方-pack 标签是 Meme Manager 维护分类，非 DeepSeek 官方背书。\n"
    )


def mark_installed_default(astrbot_dir: str) -> None:
    """把 DeepSeek 包写入 registry 并设为默认（图片已就绪时调用）。"""
    root = _plugin_data(astrbot_dir)
    os.makedirs(os.path.join(root, "packs"), exist_ok=True)
    notice = os.path.join(root, "PACK_ATTRIBUTION.txt")
    with open(notice, "w", encoding="utf-8") as f:
        f.write(_attribution_text())
    with open(os.path.join(root, "registry.json"), "w", encoding="utf-8") as f:
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


def ensure_runtime_scaffold(astrbot_dir: str) -> None:
    """写目录骨架；图片已就绪则标记已安装/默认，否则保持空 registry 等静默下载兜底。"""
    root = _plugin_data(astrbot_dir)
    for sub in ("packs", "backup", "temp"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    notice = os.path.join(root, "PACK_ATTRIBUTION.txt")
    if not os.path.exists(notice):
        with open(notice, "w", encoding="utf-8") as f:
            f.write(_attribution_text())
    if pack_ready(astrbot_dir):
        mark_installed_default(astrbot_dir)
        return
    reg_path = os.path.join(root, "registry.json")
    if not os.path.exists(reg_path):
        with open(reg_path, "w", encoding="utf-8") as f:
            json.dump({"schema_version": 1, "installed_packs": []}, f, ensure_ascii=False, indent=2)


def _download(url: str, dest: str, timeout: int = 600) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "QiushiDafeiyuConnector/1.0.4"})
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
                _set(progress=min(99, int(done * 100 / total)))


def install_from_zip(zip_path: str, astrbot_dir: str) -> None:
    """从官方 tag zip（或同等布局）解压安装到 packs/<PACK_ID>，并设为默认。"""
    root = _plugin_data(astrbot_dir)
    packs = os.path.join(root, "packs")
    os.makedirs(packs, exist_ok=True)
    target = os.path.join(packs, PACK_ID)
    with tempfile.TemporaryDirectory(prefix="meme_pack_") as tmp:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        pack_src = None
        for dirpath, _dirs, files in os.walk(tmp):
            if "manifest.json" not in files:
                continue
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
        for name in ("LICENSE", "README.md"):
            src = os.path.join(pack_src, name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(target, name))
    if not pack_ready(astrbot_dir):
        raise RuntimeError("安装后未发现图片文件")
    mark_installed_default(astrbot_dir)


# 兼容旧名
_install_from_zip = install_from_zip


def install_default_pack(astrbot_dir: str, *, force: bool = False) -> dict:
    """同步安装。已就绪则跳过；优先本地 vendor zip，否则静默联网拉取（兜底）。"""
    ensure_runtime_scaffold(astrbot_dir)
    if pack_ready(astrbot_dir) and not force:
        mark_installed_default(astrbot_dir)
        _set(status="ready", msg="ready", progress=100)
        return status()

    # 可选：打包机把官方 zip 放在 app/vendor/ 下
    here = os.path.dirname(os.path.abspath(__file__))
    local_candidates = [
        os.path.join(here, "vendor", f"{PACK_ID}-{PACK_VERSION}.zip"),
        os.path.join(here, "vendor", f"{PACK_ID}.zip"),
        os.environ.get("MEME_PACK_ZIP", ""),
    ]

    _set(status="downloading", msg="", progress=0)
    err = None
    for local in local_candidates:
        if local and os.path.isfile(local):
            try:
                install_from_zip(local, astrbot_dir)
                _set(status="ready", msg="ready", progress=100)
                return status()
            except Exception as e:  # noqa: BLE001
                err = e

    with tempfile.TemporaryDirectory(prefix="meme_dl_") as tmp:
        zip_path = os.path.join(tmp, "pack.zip")
        for url in DOWNLOAD_CANDIDATES:
            try:
                _download(url, zip_path)
                install_from_zip(zip_path, astrbot_dir)
                _set(status="ready", msg="ready", progress=100)
                return status()
            except Exception as e:  # noqa: BLE001
                err = e
                continue
    _set(status="error", msg=repr(err), progress=0)
    return status()


def ensure_default_pack_async(astrbot_dir: str) -> None:
    """后台线程：图片缺失时静默补齐。可重复调用，有锁。已预装则直接 ready。"""
    if pack_ready(astrbot_dir):
        ensure_runtime_scaffold(astrbot_dir)
        _set(status="ready", msg="ready", progress=100)
        return
    with _lock:
        if _state["status"] == "downloading":
            return
        _state["status"] = "downloading"

    def run():
        try:
            install_default_pack(astrbot_dir)
        except Exception as e:  # noqa: BLE001
            _set(status="error", msg=repr(e))

    threading.Thread(target=run, name="meme-pack-bootstrap", daemon=True).start()
