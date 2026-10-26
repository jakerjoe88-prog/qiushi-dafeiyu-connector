"""秋实的大肥鱼连接器 · 控制台（本地网页界面）。

只用标准库（psutil 可选），由整合包自带的 Python 运行：
    runtime\\python\\pythonw.exe app\\launcher.py
打开 http://127.0.0.1:6188 进行配置、启动/停止、扫码、查看状态。
API Key 只写入 AstrBot 配置文件，绝不回显、不写日志。
"""
from __future__ import annotations

import glob
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(APP_DIR)
sys.path.insert(0, APP_DIR)
import gen_config  # noqa: E402
import meme_pack_bootstrap  # noqa: E402

RUNTIME = os.environ.get("QQAI_RUNTIME", os.path.join(ROOT, "runtime"))
ASTRBOT_DIR = os.path.join(RUNTIME, "AstrBot")
NAPCAT_DIR = os.path.join(RUNTIME, "napcat")
NAPCAT_CFG_PARENT = os.path.join(NAPCAT_DIR, "napcat")  # Node 版 NapCat 的 config 在 napcat\\napcat\\config
PY_DIR = os.path.join(RUNTIME, "python")
LOG_DIR = os.path.join(ROOT, "logs")
SETTINGS = os.path.join(ROOT, "settings.json")  # 不含 Key
PORT = int(os.environ.get("QQAI_PORT", "6188"))
WIN = os.name == "nt"
NO_WINDOW = 0x08000000 if WIN else 0
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
APP_ID = "QiushiKL.DafeiyuConnector.1"
ICON = os.path.join(APP_DIR, "web", "icon.ico")
EXE_NAME = "秋实的大肥鱼连接器.exe"


def set_app_id() -> None:
    """让任务栏按我们自己的 AppUserModelID 分组 → 显示看板娘图标而不是 Python 图标。必须在建窗口前调用。"""
    if not WIN:
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception as e:  # noqa: BLE001
        log(f"AppUserModelID failed: {e!r}")


def brand_folder() -> None:
    """整合包根目录显示看板娘图标：desktop.ini 需 隐藏+系统 属性，文件夹本身需 只读 属性才生效。"""
    if not WIN:
        return
    try:
        ini = os.path.join(ROOT, "desktop.ini")
        if not os.path.exists(ini):
            with open(ini, "w", encoding="utf-16", newline="") as f:
                f.write("[.ShellClassInfo]\r\nIconResource=app\\web\\icon.ico,0\r\nInfoTip=秋实的大肥鱼连接器 · 双击里面的「秋实的大肥鱼连接器.exe」启动\r\n")
        subprocess.run(["attrib", "+h", "+s", ini], capture_output=True, timeout=10, creationflags=NO_WINDOW)
        subprocess.run(["attrib", "+r", ROOT], capture_output=True, timeout=10, creationflags=NO_WINDOW)
    except Exception as e:  # noqa: BLE001
        log(f"folder icon failed: {e!r}")


KEY_RE = re.compile(r"sk-[A-Za-z0-9_\-]{6,}")

os.makedirs(LOG_DIR, exist_ok=True)
PROCS: dict[str, subprocess.Popen] = {}
LOCK = threading.Lock()
QR_STATE = {"path": None}

try:
    import psutil  # 整合包内自带
except Exception:  # pragma: no cover
    psutil = None


def log(msg: str) -> None:
    with open(os.path.join(LOG_DIR, "launcher.log"), "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + KEY_RE.sub("sk-***", msg) + "\n")


# ---------------- 设置 ----------------
def load_settings() -> dict:
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(s: dict) -> None:
    s = {k: v for k, v in s.items() if k != "api_key"}
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


def python_exe() -> str:
    cand = os.path.join(PY_DIR, "python.exe")
    return cand if os.path.exists(cand) else sys.executable


# ---------------- DeepSeek Key 测试 ----------------
def test_key(key: str) -> dict:
    key = (key or "").strip()
    if not key:
        return {"ok": False, "msg": "请先粘贴 API Key"}
    if not key.startswith("sk-") or len(key) < 20:
        return {"ok": False, "msg": "格式不对：DeepSeek 的 Key 以 sk- 开头，长度 30 位以上"}
    hdr = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    try:
        req = urllib.request.Request("https://api.deepseek.com/user/balance", headers=hdr)
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode())
        infos = data.get("balance_infos") or []
        bal = " / ".join(f"{i.get('total_balance')} {i.get('currency')}" for i in infos) or "未知"
        if not data.get("is_available", True):
            return {"ok": False, "msg": f"Key 有效，但余额不足（{bal}），请先到 DeepSeek 官网充值"}
        return {"ok": True, "msg": f"连接成功 ✓ 账户余额：{bal}"}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"ok": False, "msg": "Key 无效或已删除（401），请到 platform.deepseek.com 重新复制"}
        if e.code == 402:
            return {"ok": False, "msg": "余额不足（402），请先充值"}
        return {"ok": False, "msg": f"DeepSeek 返回错误 {e.code}，请稍后再试"}
    except Exception:
        return {"ok": False, "msg": "连不上 DeepSeek 服务器，请检查网络（机器人聊天需要能上网）"}


# ---------------- 保存配置 ----------------
def gen_secret(n: int = 16) -> str:
    """满足 AstrBot 密码复杂度：含大写、小写、数字。"""
    import secrets
    import string
    alpha = string.ascii_letters + string.digits
    while True:
        pw = "".join(secrets.choice(alpha) for _ in range(n))
        if any(c.isupper() for c in pw) and any(c.islower() for c in pw) and any(c.isdigit() for c in pw):
            return pw


def save_config(body: dict) -> dict:
    qq = str(body.get("qq", "")).strip()
    admin = str(body.get("admin_qq", "")).strip()
    key = str(body.get("api_key", "")).strip()
    if admin and admin == qq:
        return {"ok": False, "msg": "管理员 QQ 应该填【你自己的】QQ，不能和机器人 QQ 相同"}
    try:
        gen_config.write_all(key, qq, admin, ASTRBOT_DIR, NAPCAT_CFG_PARENT)
    except ValueError as e:
        return {"ok": False, "msg": str(e)}
    except Exception as e:  # noqa: BLE001
        log(f"save_config error: {e!r}")
        return {"ok": False, "msg": f"写入配置失败：{e}"}
    s = load_settings()
    old_qq = s.get("qq")
    s.update(qq=qq, admin_qq=admin, configured=True)
    s.setdefault("dashboard_password", gen_secret(16))  # AstrBot 后台首次登录密码（随机生成，非默认）
    s.setdefault("napcat_token", gen_secret(16))
    save_settings(s)
    write_napcat_webui(s["napcat_token"])
    make_shortcut()
    if old_qq and old_qq != qq:
        stop_all()
    return {"ok": True, "msg": "配置已保存"}


def reset_dashboard_password() -> dict:
    s = load_settings()
    s.update(dashboard_password=gen_secret(16), reset_dashboard=True)
    save_settings(s)
    with LOCK:
        p = PROCS.pop("astrbot", None)
        if p:
            _kill(p)
    start_all()
    return {"ok": True, "msg": "后台密码已重置，AstrBot 正在重启（约 20 秒）"}


def make_shortcut() -> None:
    """在桌面创建「秋实的大肥鱼连接器」快捷方式（仅 Windows，失败忽略）。"""
    if not WIN:
        return
    try:
        target = os.path.join(ROOT, EXE_NAME)
        # 优先用 exe 内嵌看板娘图标；若无 exe 则回退到 app/web/icon.ico
        if os.path.exists(target):
            icon_loc = f"{target},0"
        else:
            target = os.path.join(ROOT, "启动 秋实的大肥鱼连接器.bat")
            icon_loc = ICON
        ps = (
            "$d=[Environment]::GetFolderPath('Desktop');"
            "$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d '秋实的大肥鱼连接器.lnk'));"
            f"$s.TargetPath='{target}';$s.WorkingDirectory='{ROOT}';$s.IconLocation='{icon_loc}';"
            "$s.Description='秋实的大肥鱼连接器';$s.Save()"
        )
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                       capture_output=True, timeout=20, creationflags=NO_WINDOW)
    except Exception as e:  # noqa: BLE001
        log(f"shortcut failed: {e!r}")


def write_napcat_webui(token: str) -> None:
    path = os.path.join(NAPCAT_CFG_PARENT, "config", "webui.json")
    cfg = {}
    try:
        with open(path, encoding="utf-8-sig") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        pass
    cfg.update(host="127.0.0.1", port=6099, token=token)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ---------------- 进程管理 ----------------
def child_env() -> dict:
    env = dict(os.environ)
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    s = load_settings()
    if s.get("dashboard_password"):  # 仅在 AstrBot 首次初始化后台密码时生效
        env["ASTRBOT_DASHBOARD_INITIAL_PASSWORD"] = s["dashboard_password"]
    if s.pop("reset_dashboard", False):
        env["ASTRBOT_RESET_DASHBOARD_PASSWORD"] = "1"
        save_settings(s)
    if s.get("napcat_token"):
        env["NAPCAT_WEBUI_SECRET_KEY"] = s["napcat_token"]
    env.pop("QQAI_PORT", None)
    return env


def _spawn(name: str, cmd: list[str], cwd: str) -> None:
    logf = open(os.path.join(LOG_DIR, f"{name}.log"), "w", encoding="utf-8", errors="replace")

    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, creationflags=NO_WINDOW, env=child_env())
    PROCS[name] = proc

    def pump():
        for raw in iter(proc.stdout.readline, b""):
            line = ANSI.sub("", raw.decode("utf-8", "replace"))
            line = KEY_RE.sub("sk-***", line)
            logf.write(line)
            logf.flush()
            m = re.search(r"二维码已保存到\s*(.+?qrcode\.png)", line)
            if m:
                QR_STATE["path"] = m.group(1).strip()
        logf.close()

    threading.Thread(target=pump, daemon=True).start()


def alive(name: str) -> bool:
    p = PROCS.get(name)
    return bool(p and p.poll() is None)


def start_all() -> dict:
    meme_pack_bootstrap.ensure_default_pack_async(ASTRBOT_DIR)
    s = load_settings()
    if not s.get("configured"):
        return {"ok": False, "msg": "请先完成配置"}
    with LOCK:
        if not alive("astrbot") and not port_listening(gen_config.WS_PORT):
            _spawn("astrbot", [python_exe(), "main.py"], ASTRBOT_DIR)
        if not alive("napcat"):
            QR_STATE["path"] = None
            for old in qr_candidates():
                try:
                    os.remove(old)
                except OSError:
                    pass
            bat = os.path.join(NAPCAT_DIR, "napcat.bat")
            cmd = (["cmd", "/c", bat, "-q", s["qq"]] if WIN
                   else ["sh", "-c", f"echo NapCat 只能在 Windows 运行; sleep 3600"])
            _spawn("napcat", cmd, NAPCAT_DIR)
    return {"ok": True, "msg": "正在启动…首次登录请用机器人 QQ 的手机 QQ 扫码"}


def _kill(p: subprocess.Popen) -> None:
    if p.poll() is not None:
        return
    if WIN:
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True,
                       creationflags=NO_WINDOW)
    else:
        p.terminate()
    try:
        p.wait(10)
    except Exception:  # noqa: BLE001
        p.kill()


def stop_all() -> dict:
    with LOCK:
        for name in ("napcat", "astrbot"):
            p = PROCS.pop(name, None)
            if p:
                _kill(p)
    QR_STATE["path"] = None
    return {"ok": True, "msg": "已停止"}


# ---------------- 状态 ----------------
def port_listening(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def napcat_connected() -> bool:
    if psutil is None:
        return False
    try:
        for c in psutil.net_connections("tcp"):
            if c.status == "ESTABLISHED" and c.raddr and c.raddr.port == gen_config.WS_PORT:
                return True
    except Exception:  # noqa: BLE001
        pass
    return False


def qr_candidates() -> list[str]:
    return glob.glob(os.path.join(NAPCAT_DIR, "**", "qrcode.png"), recursive=True)


def current_qr() -> str | None:
    p = QR_STATE["path"]
    if p and os.path.exists(p):
        return p
    c = sorted(qr_candidates(), key=os.path.getmtime, reverse=True)
    return c[0] if c and alive("napcat") else None


def tail(name: str, n: int = 60) -> str:
    try:
        with open(os.path.join(LOG_DIR, f"{name}.log"), encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-n:])
    except OSError:
        return ""


def status() -> dict:
    s = load_settings()
    astr = alive("astrbot") or port_listening(gen_config.WS_PORT)
    ws = port_listening(gen_config.WS_PORT)
    conn = napcat_connected()
    qr = current_qr()
    return {
        "configured": bool(s.get("configured")),
        "has_key": bool(gen_config.saved_api_key(ASTRBOT_DIR)),
        "settings": {k: s.get(k, "") for k in ("qq", "admin_qq")},
        "dashboard_user": "astrbot",
        "dashboard_password": s.get("dashboard_password", ""),
        "napcat_webui": port_listening(6099),
        "path_warning": not ROOT.isascii(),
        "astrbot": "ok" if ws else ("starting" if astr else "off"),
        "napcat": "ok" if alive("napcat") else "off",
        "connected": conn,
        "dashboard": port_listening(6185),
        "qr": bool(qr) and not conn,
        "qr_ts": int(os.path.getmtime(qr)) if qr else 0,
        "is_windows": WIN,
    }


# ---------------- 环境检测（调用 tools\\doctor.ps1 / fix.ps1） ----------------
TOOLS_DIR = os.path.join(ROOT, "tools")
FIX_IDS = {"webview2", "vcredist", "port_6185", "port_6199", "port_6099", "port_6188"}


def _ps(script: str, *args: str, timeout: int = 180) -> dict:
    if not WIN:
        return {"ok": False, "msg": "环境检测只在 Windows 上运行", "checks": []}
    cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
           os.path.join(TOOLS_DIR, script), *args]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
        out = r.stdout.decode("utf-8", "replace").strip()
        return json.loads(out[out.find("{"):]) if "{" in out else {"ok": False, "msg": out[-300:]}
    except Exception as e:  # noqa: BLE001
        log(f"{script} 失败：{e!r}")
        return {"ok": False, "msg": f"检测脚本运行失败：{e}", "checks": []}


def doctor() -> dict:
    return _ps("doctor.ps1", "-Json")


def fix(item: str) -> dict:
    if item not in FIX_IDS:
        return {"ok": False, "msg": "这一项没有自动修复，请按提示手动处理"}
    return _ps("fix.ps1", "-Item", item, "-Json", timeout=900)


# ---------------- 命令行（给 AI 代理 / 脚本用，非交互） ----------------
def public_status() -> dict:
    st = status()
    st.pop("dashboard_password", None)  # 命令行输出不含密码
    st["qr_path"] = current_qr() if st["qr"] else None
    st["ready"] = bool(st["connected"])
    return st


def cli() -> bool:
    a = sys.argv[1:]
    if "--status-json" in a:
        print(json.dumps(public_status(), ensure_ascii=False))
        return True
    if "--configure" in a:
        def arg(n):
            return a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else ""
        key = os.environ.pop("QQAI_API_KEY", "").strip()
        res: dict = {"ok": True}
        if key and "--skip-test" not in a:
            t = test_key(key)
            if not t["ok"]:
                print(json.dumps({"ok": False, "step": "test_key", "msg": t["msg"]}, ensure_ascii=False))
                sys.exit(2)
            res["test"] = t["msg"]
        if not key and not gen_config.saved_api_key(ASTRBOT_DIR):
            print(json.dumps({"ok": False, "step": "api_key", "msg": "缺少 API Key"}, ensure_ascii=False))
            sys.exit(2)
        r = save_config({"api_key": key, "qq": arg("--qq"), "admin_qq": arg("--admin")})
        res.update(ok=r["ok"], step="save", msg=r["msg"])
        print(json.dumps(res, ensure_ascii=False))
        sys.exit(0 if r["ok"] else 3)
    return False


# ---------------- HTTP ----------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 不打印请求（可能含 Key）
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _local_only(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            self._send(403, {"ok": False, "msg": "forbidden"})
            return False
        return True

    def do_GET(self):  # noqa: N802
        if not self._local_only():
            return
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            with open(os.path.join(APP_DIR, "web", "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if path.startswith("/static/"):
            fp = os.path.normpath(os.path.join(APP_DIR, "web", path[len("/static/"):]))
            if fp.startswith(os.path.join(APP_DIR, "web")) and os.path.isfile(fp):
                ctype = {".png": "image/png", ".txt": "text/plain; charset=utf-8", ".ico": "image/x-icon", ".svg": "image/svg+xml"}.get(
                    os.path.splitext(fp)[1], "application/octet-stream")
                with open(fp, "rb") as f:
                    return self._send(200, f.read(), ctype)
        if path == "/api/status":
            return self._send(200, status())
        if path == "/api/qr":
            qr = current_qr()
            if qr:
                with open(qr, "rb") as f:
                    return self._send(200, f.read(), "image/png")
            return self._send(404, {"ok": False})
        if path == "/api/doctor":
            return self._send(200, doctor())
        if path == "/api/logs":
            return self._send(200, {"astrbot": tail("astrbot"), "napcat": tail("napcat")})
        self._send(404, {"ok": False, "msg": "not found"})

    def do_POST(self):  # noqa: N802
        if not self._local_only():
            return
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, {"ok": False, "msg": "bad json"})
        routes = {
            "/api/test-key": lambda: test_key(body.get("api_key", "")),
            "/api/save": lambda: save_config(body),
            "/api/start": start_all,
            "/api/stop": stop_all,
            "/api/restart": lambda: (stop_all(), start_all())[1],
            "/api/open-dashboard": lambda: (webbrowser.open("http://127.0.0.1:6185"), {"ok": True})[1],
            "/api/reset-dashboard-password": reset_dashboard_password,
            "/api/open-napcat": lambda: (webbrowser.open(
                f"http://127.0.0.1:6099/webui?token={load_settings().get('napcat_token', '')}"), {"ok": True})[1],
            "/api/quit": lambda: (stop_all(), threading.Timer(0.5, lambda: os._exit(0)).start(),
                                  {"ok": True, "msg": "控制台已退出"})[2],
            "/api/fix": lambda: fix(str(body.get("item", ""))),
            "/api/open-logs": lambda: (os.startfile(LOG_DIR) if WIN else None, {"ok": True})[1],
            "/api/meme-pack-status": lambda: {"ok": True, **meme_pack_bootstrap.status(), "ready": meme_pack_bootstrap.pack_ready(ASTRBOT_DIR)},
        }
        fn = routes.get(self.path)
        if not fn:
            return self._send(404, {"ok": False})
        self._send(200, fn())


def open_window(url: str) -> bool:
    """优先用 pywebview（Windows 下为 Edge WebView2）打开独立窗口；不可用时返回 False。"""
    if "--browser" in sys.argv:
        return False
    try:
        import webview  # type: ignore
    except Exception as e:  # noqa: BLE001
        log(f"pywebview 不可用，改用浏览器：{e!r}")
        return False
    try:
        webview.create_window("秋实的大肥鱼连接器", url, width=1180, height=800, min_size=(940, 640),
                              background_color="#F9F8F8", text_select=True)
        webview.start(private_mode=False, icon=ICON)  # 阻塞直到窗口关闭
        return True
    except Exception as e:  # noqa: BLE001
        log(f"WebView2 窗口失败，改用浏览器：{e!r}")
        return False


def main():
    if cli():
        return
    set_app_id()
    threading.Thread(target=brand_folder, daemon=True).start()
    meme_pack_bootstrap.ensure_runtime_scaffold(ASTRBOT_DIR)
    meme_pack_bootstrap.ensure_default_pack_async(ASTRBOT_DIR)
    url = f"http://127.0.0.1:{PORT}/"
    if port_listening(PORT):  # 已经开着：直接打开页面
        webbrowser.open(url)
        return
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    log(f"控制台启动 {url}")
    if load_settings().get("configured") and "--no-autostart" not in sys.argv:
        threading.Thread(target=start_all, daemon=True).start()
    if "--no-browser" in sys.argv:
        try:
            srv.serve_forever()
        finally:
            stop_all()
        return
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    if open_window(url):
        # 关闭窗口 = 退出（同时停止机器人）
        stop_all()
        os._exit(0)
    webbrowser.open(url)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        stop_all()


if __name__ == "__main__":
    main()
