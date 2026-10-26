"""用 Chrome DevTools 协议精确渲染截图 + 录制交互动画（仅开发用，不进整合包）。
用法: python cdp_shots.py <base_url> <out_dir> [shots|flow|astrbot]"""
import asyncio, base64, json, os, subprocess, sys, time, aiohttp

BASE, OUT, MODE = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "shots")
W, H = 1180, 820
os.makedirs(OUT, exist_ok=True)


class Page:
    def __init__(s, ws):
        s.ws, s.i, s.fut, s.frames = ws, 0, {}, []
        s.reader = asyncio.create_task(s._read())
    async def _read(s):
        async for m in s.ws:
            msg = json.loads(m.data)
            if "id" in msg and msg["id"] in s.fut:
                s.fut.pop(msg["id"]).set_result(msg.get("result", {}))
            elif msg.get("method") == "Page.screencastFrame":
                pr = msg["params"]; s.frames.append((pr["metadata"]["timestamp"], pr["data"]))
                asyncio.create_task(s.send("Page.screencastFrameAck", sessionId=pr["sessionId"]))
    async def send(s, m, **p):
        s.i += 1; mid = s.i; f = asyncio.get_event_loop().create_future(); s.fut[mid] = f
        await s.ws.send_json({"id": mid, "method": m, "params": p})
        return await f
    async def js(s, expr):
        r = await s.send("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        return r.get("result", {}).get("value")
    async def goto(s, url, wait=2.2):
        await s.send("Page.navigate", url=url); await asyncio.sleep(wait)
    async def shot(s, name):
        r = await s.send("Page.captureScreenshot", format="png")
        open(os.path.join(OUT, name + ".png"), "wb").write(base64.b64decode(r["data"])); print("shot", name)


async def main():
    port = 9333
    chrome = subprocess.Popen(["google-chrome", "--headless=new", "--no-sandbox", f"--remote-debugging-port={port}",
                               "--hide-scrollbars", f"--window-size={W},{H}", "--user-data-dir=/tmp/cdp-prof", "about:blank"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        async with aiohttp.ClientSession() as cs:
            for _ in range(50):
                try:
                    tabs = await (await cs.get(f"http://127.0.0.1:{port}/json")).json(); break
                except Exception: await asyncio.sleep(0.2)
            tab = [t for t in tabs if t["type"] == "page"][0]
            async with cs.ws_connect(tab["webSocketDebuggerUrl"], max_msg_size=0) as ws:
                p = Page(ws)
                await p.send("Page.enable")
                await p.send("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=1, mobile=False)
                if MODE == "shots":
                    for theme in ("v2",):
                        for d in ["welcome", "step1", "step1load", "step1ok", "step1bad", "step1err", "step2", "step2err",
                                  "step2same", "step3", "step3ok", "panel", "panelpw", "panelqr", "panelstart", "paneloff", "about",
                                  "doctor", "doctorfix", "ai"]:
                            await p.goto(f"{BASE}?demo={d}&theme={theme}", 2.4)
                            await p.shot(d)
                        await p.goto(f"{BASE}?demo=panel&theme={theme}", 2.0)
                        h = await p.js("document.documentElement.scrollHeight")
                        await p.send("Emulation.setDeviceMetricsOverride", width=W, height=h, deviceScaleFactor=1, mobile=False)
                        await asyncio.sleep(1.2); await p.shot("panel-full")
                        await p.send("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=1, mobile=False)
                elif MODE == "flow":
                    await p.goto(f"{BASE}?demo=flow&", 1.5)
                    await p.send("Page.startScreencast", format="jpeg", quality=90, maxWidth=W, maxHeight=H, everyNthFrame=1)
                    async def hold(sec): await asyncio.sleep(sec)
                    t0 = time.time()
                    await hold(2.2)
                    await p.js('document.getElementById("go").click()'); await hold(1.6)
                    key = "sk-3f9a1c0e7b2d4a6f8e1c3b5d7a9f0e2c"
                    for i in range(0, len(key), 4):
                        await p.js(f'(()=>{{const k=document.getElementById("key");k.value={json.dumps(key[:i+4])};k.dispatchEvent(new Event("input"))}})()'); await hold(0.08)
                    await p.js('document.getElementById("testBtn").click()'); await hold(2.4)
                    await p.js('document.getElementById("next1").click()'); await hold(1.3)
                    for i in range(1, 10):
                        await p.js(f'document.getElementById("qq").value="123456789".slice(0,{i})'); await hold(0.06)
                    await p.js('document.getElementById("admin").focus()')
                    for i in range(1, 10):
                        await p.js(f'document.getElementById("admin").value="987654321".slice(0,{i})'); await hold(0.06)
                    await p.js('document.getElementById("qq").blur();document.getElementById("admin").blur();checkQQ()'); await hold(1.2)
                    await p.js('document.getElementById("next2").click()'); await hold(6.5)
                    await p.js('document.getElementById("toPanel").click()'); await hold(3.5)
                    await p.js('document.getElementById("navDoc").click()'); await hold(3.2)
                    await p.js('document.getElementById("navAi").click()'); await hold(2.8)
                    await p.send("Page.stopScreencast")
                    fdir = os.path.join(OUT, "frames"); os.makedirs(fdir, exist_ok=True)
                    # 按时间戳重采样为恒定 25fps
                    fr = sorted(s.frames if False else p.frames); t0f = fr[0][0]; k = 0; j = 0
                    end = fr[-1][0] - t0f
                    while k / 25 <= end:
                        while j + 1 < len(fr) and fr[j + 1][0] - t0f <= k / 25: j += 1
                        open(f"{fdir}/{k:05d}.jpg", "wb").write(base64.b64decode(fr[j][1])); k += 1
                    print("raw", len(fr), "out", k)
                elif MODE == "astrbot":
                    pw = os.environ["DASH_PW"]; newpw = os.environ.get("DASH_NEWPW", pw)
                    await p.goto("http://127.0.0.1:6185/", 4)
                    await p.shot("astrbot-login")
                    print(await p.js("document.body.innerText.slice(0,300)"))
    finally:
        chrome.kill()

asyncio.run(main())
