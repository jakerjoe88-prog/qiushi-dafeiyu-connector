import json, os, shutil, subprocess, sys
import pytest

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)
UP = os.path.join(HERE, "upstream")
sys.path.insert(0, os.path.join(ROOT, "core"))
import gen_config as g  # noqa: E402

KEY = "sk-" + "a" * 32
QQ = "123456789"


@pytest.fixture(scope="session", autouse=True)
def upstream():
    subprocess.run(["bash", os.path.join(HERE, "fetch_upstream.sh")], check=True)


def test_validate_inputs():
    g.validate_inputs(KEY, QQ, "10001")
    for bad in [("abc", QQ), (KEY, "0123"), (KEY, "12a45")]:
        with pytest.raises(ValueError):
            g.validate_inputs(*bad)


def test_astrbot_config_against_upstream_default():
    default = g.load_astrbot_default(os.path.join(UP, "astrbot"))
    assert default, "must import real upstream DEFAULT_CONFIG"
    cfg = g.build_astrbot_config(KEY, QQ, "10001", os.path.join(UP, "astrbot"))

    def keys(d, p=""):
        for k, v in d.items():
            yield p + k
            if isinstance(v, dict) and v and k not in ("config_template", "custom_extra_body"):
                yield from keys(v, p + k + ".")
    # 所有补丁键都必须是上游已有的键（provider 列表项除外）
    patch_keys = set(keys({k: v for k, v in g.astrbot_patch(KEY, QQ).items() if not isinstance(v, list)}))
    missing = patch_keys - set(keys(default))
    assert not missing, missing
    assert cfg["config_version"] == default["config_version"]
    # 平台：与上游 OneBot v11 模板字段一致
    import re
    src = open(os.path.join(UP, "astrbot/astrbot/core/config/default.py"), encoding="utf-8").read()
    for f in ("ws_reverse_host", "ws_reverse_port", "ws_reverse_token"):
        assert f in src and f in cfg["platform"][0]
    assert cfg["platform"][0]["type"] == "aiocqhttp" and cfg["platform"][0]["ws_reverse_port"] == 6199
    # DeepSeek 源与上游模板一致
    assert '"provider": "deepseek"' in src
    ps = cfg["provider_sources"][0]
    assert ps["key"] == [KEY] and ps["api_base"] == "https://api.deepseek.com/v1"
    assert cfg["provider"][0]["provider_source_id"] == ps["id"]
    assert cfg["agent_runner"]["config"]["model"]["provider_id"] == cfg["provider"][0]["id"]
    # 插件要求
    assert cfg["platform_settings"]["empty_mention_waiting"] is False
    assert cfg["provider_ltm_settings"]["active_reply"]["enable"] is False
    assert cfg["provider_ltm_settings"]["group_icl_enable"] is True
    assert "10001" in cfg["admins_id"]
    # 上游默认里的其他键保留
    assert cfg["dashboard"]["port"] == default["dashboard"]["port"]
    assert cfg["agent_runner"]["config"]["persona"]["safety_mode"] is True


def test_astrbot_upstream_merge_logic_accepts_config(tmp_path):
    """用上游 provider 合并逻辑（migra_helper._get_effective_provider_map）解析生成的配置。"""
    sys.path.insert(0, os.path.join(UP, "astrbot"))
    try:
        from astrbot.core.utils import migra_helper
    except Exception as e:  # 依赖不全时跳过
        pytest.skip(f"astrbot deps missing: {e}")
    finally:
        sys.path.pop(0)
    cfg = g.build_astrbot_config(KEY, QQ)
    m = migra_helper._get_effective_provider_map(cfg)
    p = m[g.PROVIDER_ID]
    assert p["key"] == [KEY] and p["model"] == g.DEFAULT_MODEL and p["provider"] == "deepseek"


def test_plugin_config_against_real_schema():
    schema = json.load(open(os.path.join(UP, "_conf_schema.json"), encoding="utf-8-sig"))
    for k in g.PLUGIN_OVERRIDES:
        assert k in schema, f"override key {k} not in upstream schema"
        t = schema[k].get("type")
        v = g.PLUGIN_OVERRIDES[k]
        assert {"bool": bool, "int": int, "float": (int, float)}.get(t, object) and isinstance(
            v, {"bool": bool, "int": int, "float": (int, float), "string": str, "text": str, "list": list}.get(t, object)), k
    cfg = g.build_plugin_config(schema, "10001")
    assert set(cfg) <= set(schema)
    assert cfg["enable_private_chat"] is False and cfg["enable_group_chat"] is True
    assert cfg["plugin_gcp_reset_allowed_user_ids"] == ["10001"]


def test_napcat_config_against_real_typebox_schema(tmp_path):
    cfg = g.build_napcat_onebot(QQ)
    ws = cfg["network"]["websocketClients"][0]
    assert ws["url"] == "ws://127.0.0.1:6199/ws" and ws["messagePostFormat"] == "array"
    assert ws["reconnectInterval"] == 5000 and ws["heartInterval"] == 5000
    if not shutil.which("node") or not os.path.isdir(os.path.join(UP, "node_modules", "@sinclair")):
        pytest.skip("node/typebox unavailable")
    p = tmp_path / "onebot.json"; p.write_text(json.dumps(cfg))
    shutil.copy(os.path.join(HERE, "napcat_validate.mjs"), UP)
    r = subprocess.run(["node", os.path.join(UP, "napcat_validate.mjs"),
                        os.path.join(UP, "napcat_onebot_config.ts"), str(p)],
                       capture_output=True, text=True, cwd=UP)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["url"] == ws["url"]


def test_cli_end_to_end(tmp_path):
    astr = tmp_path / "AstrBot"; nap = tmp_path / "napcat"
    plug = astr / "data/plugins/astrbot_plugin_group_chat_plus"; plug.mkdir(parents=True)
    shutil.copy(os.path.join(UP, "_conf_schema.json"), plug)
    shutil.copytree(os.path.join(UP, "astrbot/astrbot"), astr / "astrbot")
    g.main(["--api-key", KEY, "--qq", QQ, "--persona", "阿星", "--astrbot-dir", str(astr), "--napcat-dir", str(nap)])
    assert json.load(open(astr / "data/cmd_config.json"))["platform"][0]["id"] == "napcat"
    assert (astr / "data/config/astrbot_plugin_group_chat_plus_config.json").exists()
    assert (nap / f"config/onebot11_{QQ}.json").exists()
    assert "阿星" in json.load(open(astr / "data/oneclick_persona.json"))["prompt"]
    # 再跑一次（已有配置时合并而不是覆盖）
    g.main(["--api-key", "sk-" + "b" * 32, "--qq", QQ, "--astrbot-dir", str(astr), "--napcat-dir", str(nap)])
    c = json.load(open(astr / "data/cmd_config.json"))
    assert c["provider_sources"][0]["key"] == ["sk-" + "b" * 32] and len(c["platform"]) == 1
