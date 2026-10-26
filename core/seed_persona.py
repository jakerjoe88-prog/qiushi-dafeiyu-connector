"""用 AstrBot 自带数据库接口写入默认人格（需在 AstrBot 目录、用其 venv 运行）。"""
import asyncio, json, os, sys

async def main(astrbot_dir):
    sys.path.insert(0, astrbot_dir)
    os.chdir(astrbot_dir)
    from astrbot.core.db.sqlite import SQLiteDatabase
    info = json.load(open(os.path.join("data", "oneclick_persona.json"), encoding="utf-8"))
    db = SQLiteDatabase(os.path.join("data", "data_v4.db"))
    await db.initialize()
    if await db.get_persona_by_id(info["persona_id"]):
        await db.delete_persona(info["persona_id"])
    await db.insert_persona(persona_id=info["persona_id"], system_prompt=info["prompt"])
    print("persona OK:", info["name"])

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
