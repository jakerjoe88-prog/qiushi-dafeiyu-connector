"""一键包配置生成器（纯标准库，Linux 可测试）。

生成：
  * AstrBot  data/cmd_config.json
  * 插件     data/config/astrbot_plugin_group_chat_plus_config.json
  * NapCat   napcat/config/onebot11_<qq>.json
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys

PLUGIN_NAME = "astrbot_plugin_group_chat_plus"
PROVIDER_SOURCE_ID = "deepseek_source"
PROVIDER_ID = "deepseek_flash"
DEFAULT_MODEL = "deepseek-flash"
DEFAULT_PERSONA_ID = "oneclick_persona"
WS_PORT = 6199

# ---- 省钱默认值：AstrBot ----
ASTRBOT_TUNING = {
    "max_turns": 20,          # 单会话最多保留 20 轮上下文
    "max_tokens": 600,        # 单次回复最多 600 tokens
    "rate_limit_count": 20,   # 每会话每分钟最多 20 次请求
}

# ---- 省钱默认值：group_chat_plus 插件（键名均来自上游 _conf_schema.json）----
PLUGIN_OVERRIDES = {
    "enable_group_chat": True,
    "enable_private_chat": False,         # 私聊交给 AstrBot 原生处理
    "initial_probability": 0.02,          # 普通消息进入"读空气"判断的概率（上游默认 0.02，保持）
    "after_reply_probability": 0.5,       # 回复后提升到的概率（上游 0.8 → 0.5）
    "probability_duration": 90,           # 提升持续 90 秒（上游 120）
    "enable_probability_hard_limit": True,
    "probability_min_limit": 0.01,
    "probability_max_limit": 0.5,         # 概率硬上限 0.5（上游 0.8）
    "enable_reply_density_limit": True,
    "reply_density_window_seconds": 300,
    "reply_density_max_replies": 3,       # 5 分钟内最多回 3 条
    "enable_frequency_adjuster": True,
    "frequency_check_interval": 600,      # 频率分析 AI 调用间隔 10 分钟（上游 180 秒）
    "frequency_max_probability": 0.4,
    "enable_proactive_chat": False,       # 关闭主动搭话（省钱 + 降低风控）
    "enable_proactive_ai_judge": False,
    "enable_image_processing": False,     # 不做图片转文字
    "enable_image_description_cache": True,
    "enable_decision_ai_reasoning": False,
    "enable_frequency_ai_reasoning": False,
    "enable_memory_injection": False,
    "max_context_messages": 30,           # 读空气/回复时最多带 30 条群消息（上游 -1=不限）
    "custom_storage_max_messages": 200,
    "pending_cache_max_count": 10,
    "enable_typing_simulator": True,
    "enable_typo_generator": False,       # 不故意打错字
    "enable_poke_after_reply": False,
    "enable_duplicate_filter": True,
    "enable_group_wait_window": False,
    "enable_web_panel": False,            # 插件自带 Web 面板关闭，减少暴露端口
}


def validate_inputs(api_key: str, qq: str, admin_qq: str = "") -> None:
    if not api_key or not api_key.strip().startswith("sk-") or len(api_key.strip()) < 20:
        raise ValueError("DeepSeek API Key 格式不对（应以 sk- 开头）")
    if not re.fullmatch(r"[1-9]\d{4,11}", qq or ""):
        raise ValueError("QQ 号格式不对（5-12 位数字）")
    if admin_qq and not re.fullmatch(r"[1-9]\d{4,11}", admin_qq):
        raise ValueError("管理员 QQ 号格式不对")


def deep_merge(base: dict, patch: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_astrbot_default(astrbot_dir: str | None) -> dict:
    """从已下载的 AstrBot 源码读取真实 DEFAULT_CONFIG。

    只加载 astrbot/core/config/default.py 及其少量纯标准库依赖，
    用空壳包绕过 astrbot.core.__init__（那里会初始化数据库/日志）。
    拿不到则返回空 dict（AstrBot 启动时 check_config_integrity 会补齐缺失键）。"""
    if not astrbot_dir:
        return {}
    import importlib
    import types
    saved = {k: v for k, v in sys.modules.items() if k == "astrbot" or k.startswith("astrbot.")}
    for k in saved:
        del sys.modules[k]
    try:
        pkg_root = os.path.join(astrbot_dir, "astrbot")
        init_src = open(os.path.join(pkg_root, "__init__.py"), encoding="utf-8").read()
        ver = re.search(r'__version__\s*=\s*"([^"]+)"', init_src)
        for name in ("astrbot", "astrbot.core", "astrbot.core.config", "astrbot.core.utils",
                     "astrbot.core.computer", "astrbot.core.computer.booters"):
            m = types.ModuleType(name)
            m.__path__ = [os.path.join(astrbot_dir, *name.split("."))]
            sys.modules[name] = m
        sys.modules["astrbot"].__version__ = ver.group(1) if ver else "0"
        mod = importlib.import_module("astrbot.core.config.default")
        return copy.deepcopy(mod.DEFAULT_CONFIG)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] 无法读取 AstrBot 默认配置，使用最小配置: {e}", file=sys.stderr)
        return {}
    finally:
        for k in [k for k in sys.modules if k == "astrbot" or k.startswith("astrbot.")]:
            del sys.modules[k]
        sys.modules.update(saved)


def astrbot_patch(api_key: str, qq: str, admin_qq: str = "", model: str = DEFAULT_MODEL) -> dict:
    admins = [a for a in [admin_qq] if a]
    return {
        "provider_sources": [{
            "id": PROVIDER_SOURCE_ID,
            "provider": "deepseek",
            "type": "openai_chat_completion",
            "provider_type": "chat_completion",
            "enable": True,
            "key": [api_key.strip()],
            "api_base": "https://api.deepseek.com/v1",
            "timeout": 120,
            "proxy": "",
            "custom_headers": {},
        }],
        "provider": [{
            "id": PROVIDER_ID,
            "provider_source_id": PROVIDER_SOURCE_ID,
            "provider_type": "chat_completion",
            "type": "openai_chat_completion",
            "enable": True,
            "model": model,
            "modalities": ["text", "tool"],
            # 关闭思考模式（DeepSeek 默认开启思考，会多花 token），限制输出长度
            "custom_extra_body": {"thinking": {"type": "disabled"},
                                  "max_tokens": ASTRBOT_TUNING["max_tokens"]},
        }],
        "platform": [{
            "id": "napcat",
            "type": "aiocqhttp",
            "enable": True,
            "ws_reverse_host": "0.0.0.0",
            "ws_reverse_port": WS_PORT,
            "ws_reverse_token": "",
        }],
        "platform_settings": {
            "empty_mention_waiting": False,           # 插件要求：只@机器人是否触发等待 → 关
            "empty_mention_waiting_need_reply": False,
            "enable_id_white_list": False,
            "rate_limit": {"time": 60, "count": ASTRBOT_TUNING["rate_limit_count"], "strategy": "discard"},
        },
        "provider_settings": {"enable": True, "web_search": False, "streaming_response": False},
        "provider_ltm_settings": {
            "group_icl_enable": True,                 # 群聊上下文感知 → 开
            "group_message_max_cnt": 100,
            "image_caption": False,
            "active_reply": {"enable": False},        # 内置主动回复 → 关（由插件接管）
        },
        "agent_runner": {"runner_type": "local", "config": {
            "model": {"provider_id": PROVIDER_ID},
            "persona": {"persona_id": DEFAULT_PERSONA_ID},
            "compression": {"max_turns": ASTRBOT_TUNING["max_turns"], "overflow_strategy": "truncate_by_turns"},
            "misc": {"max_steps": 8},
        }},
        "admins_id": ["astrbot", *admins],
    }


def build_astrbot_config(api_key, qq, admin_qq="", astrbot_dir=None, existing=None, model=DEFAULT_MODEL):
    base = existing if existing else load_astrbot_default(astrbot_dir)
    return deep_merge(base, astrbot_patch(api_key, qq, admin_qq, model))


def build_plugin_config(schema: dict, admin_qq: str = "", persona_name: str = "") -> dict:
    cfg = {}
    for k, v in schema.items():
        if isinstance(v, dict) and "default" in v:
            cfg[k] = copy.deepcopy(v["default"])
        elif isinstance(v, dict) and v.get("type") == "object":
            cfg[k] = {ik: copy.deepcopy(iv.get("default")) for ik, iv in v.get("items", {}).items()}
    for k, v in PLUGIN_OVERRIDES.items():
        if k in schema:  # 只写上游存在的键
            cfg[k] = v
    if admin_qq:
        for k in ("plugin_gcp_reset_allowed_user_ids", "plugin_gcp_reset_here_allowed_user_ids"):
            if k in schema:
                cfg[k] = [admin_qq]
    return cfg


def build_napcat_onebot(qq: str) -> dict:
    return {
        "network": {
            "httpServers": [], "httpSseServers": [], "httpClients": [],
            "websocketServers": [],
            "websocketClients": [{
                "name": "astrbot",
                "enable": True,
                "url": f"ws://127.0.0.1:{WS_PORT}/ws",
                "messagePostFormat": "array",
                "reportSelfMessage": False,
                "reconnectInterval": 5000,
                "token": "",
                "debug": False,
                "heartInterval": 5000,
            }],
            "plugins": [],
        },
        "musicSignUrl": "",
        "enableLocalFile2Url": False,
        "parseMultMsg": False,
        "imageDownloadProxy": "",
        "timeout": {"baseTimeout": 10000, "uploadSpeedKBps": 256,
                    "downloadSpeedKBps": 256, "maxTimeout": 1800000},
    }


def persona_prompt(name: str) -> str:
    name = name or "小助手"
    return (f"你叫{name}，是这个 QQ 群里一个友善、简洁的聊天伙伴。"
            "回答尽量口语化、简短（一般不超过三句话），不要使用 Markdown。"
            "不知道的事情就直说不知道，不编造。")


def _dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--api-key", required=True)
    p.add_argument("--qq", required=True)
    p.add_argument("--admin-qq", default="")
    p.add_argument("--persona", default="小助手")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--astrbot-dir", required=True)
    p.add_argument("--napcat-dir", required=True)
    a = p.parse_args(argv)
    validate_inputs(a.api_key, a.qq, a.admin_qq)

    data = os.path.join(a.astrbot_dir, "data")
    cmd_path = os.path.join(data, "cmd_config.json")
    existing = None
    if os.path.exists(cmd_path):
        with open(cmd_path, encoding="utf-8-sig") as f:
            existing = json.load(f)
    _dump(cmd_path, build_astrbot_config(a.api_key, a.qq, a.admin_qq, a.astrbot_dir, existing, a.model))

    schema_path = os.path.join(data, "plugins", PLUGIN_NAME, "_conf_schema.json")
    with open(schema_path, encoding="utf-8-sig") as f:
        schema = json.load(f)
    _dump(os.path.join(data, "config", f"{PLUGIN_NAME}_config.json"),
          build_plugin_config(schema, a.admin_qq, a.persona))

    _dump(os.path.join(a.napcat_dir, "config", f"onebot11_{a.qq}.json"), build_napcat_onebot(a.qq))
    _dump(os.path.join(data, "oneclick_persona.json"),
          {"persona_id": DEFAULT_PERSONA_ID, "name": a.persona, "prompt": persona_prompt(a.persona)})
    print("OK")


if __name__ == "__main__":
    main()
