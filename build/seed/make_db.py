"""构建期生成 AstrBot 初始数据库：预置拟人人格「xiaoyu」（之后可在原版「人格设定」里随意改）。
用法：<linux venv python> build/seed/make_db.py <AstrBot源码目录> <输出 data_v4.db>"""
import asyncio, os, sys
src, out = sys.argv[1], os.path.abspath(sys.argv[2])
sys.path.insert(0, src)
PROMPT = ("你叫小鱼，是个真实的人，在QQ上和朋友聊天，不是AI助手。说话规则：像发微信一样短，一次一两句，最多三句，口语化；"
          "绝对不要用列表、加粗、标题、markdown，不要客服话；不主动介绍自己会什么功能；有自己的情绪，会吐槽、反问、接梗，偶尔一个表情；不懂就说不知道。")
from astrbot.core.db.sqlite import SQLiteDatabase
async def main():
    if os.path.exists(out): os.remove(out)
    db = SQLiteDatabase(out); await db.initialize()
    await db.insert_persona(persona_id="xiaoyu", system_prompt=PROMPT, begin_dialogs=[], tools=None, skills=[])
    await db.engine.dispose()
asyncio.run(main())
for ext in ("-wal", "-shm"):
    p = out + ext
    if os.path.exists(p): os.remove(p)
print("ok", out)
