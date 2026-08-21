from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot_bridge import BotCallProxy
from chat_key import extract_group_id, parse_chat_key
from http_util import chat_completions_url
from local_history import LocalMessageHistoryManager
from na_schema import iter_field_specs
from nested_config import NestedConfig, load_schema_defaults, parse_id_list
from overlay_config import overlay_na_config
from t2i_defaults import DEFAULT_T2I_API_PATH, DEFAULT_T2I_API_URL, resolve_t2i_endpoint


class ChatKeyTests(unittest.TestCase):
    def test_parse_chat_key_group(self) -> None:
        parsed = parse_chat_key("onebot_v11-group_123456")
        self.assertTrue(parsed.is_group)
        self.assertEqual(parsed.chat_id, "123456")
        self.assertEqual(parsed.platform_name, "onebot")
        self.assertEqual(parsed.umo, "onebot:GroupMessage:123456")

    def test_parse_chat_key_qq_official(self) -> None:
        parsed = parse_chat_key("qqbot_openclaw-group_abc")
        self.assertEqual(parsed.platform_name, "qq_official")
        self.assertEqual(parsed.chat_id, "abc")

    def test_parse_chat_key_akiyo_onebot_instance_group(self) -> None:
        parsed = parse_chat_key(
            "onebot_v11-qq_1234567890-group_9876543210"
        )
        self.assertTrue(parsed.is_group)
        self.assertEqual(parsed.adapter_key, "onebot_v11")
        self.assertEqual(parsed.instance_key, "qq_1234567890")
        self.assertEqual(parsed.chat_id, "9876543210")
        self.assertEqual(parsed.platform_name, "onebot")
        self.assertEqual(parsed.umo, "onebot:GroupMessage:9876543210")

    def test_parse_chat_key_akiyo_onebot_instance_private(self) -> None:
        parsed = parse_chat_key("onebot_v11-qq_1234567890-private_987654321")
        self.assertFalse(parsed.is_group)
        self.assertEqual(parsed.instance_key, "qq_1234567890")
        self.assertEqual(parsed.chat_id, "987654321")
        with self.assertRaises(ValueError):
            extract_group_id("onebot_v11-qq_1234567890-private_987654321")

    def test_parse_chat_key_rejects_invalid_akiyo_instance_segment(self) -> None:
        parsed = parse_chat_key("onebot_v11-QQ-1234567890-group_9876543210")
        self.assertEqual(parsed.instance_key, "")
        self.assertEqual(parsed.chat_id, "onebot_v11-QQ-1234567890-group_9876543210")

    def test_extract_group_id_rejects_private(self) -> None:
        with self.assertRaises(ValueError):
            extract_group_id("onebot_v11-private_1")

    def test_parse_id_list(self) -> None:
        self.assertEqual(parse_id_list("123\n456,789"), ["123", "456", "789"])


class OverlayTests(unittest.TestCase):
    def test_overlay_na_config_sets_model_group(self) -> None:
        cfg = SimpleNamespace(
            MODEL_GROUP="my-chat",
            GROUP_LIST_MODE="whitelist",
            GROUP_LIST="onebot:GroupMessage:1",
            ANALYSIS_DAYS=2,
            MAX_MESSAGES=500,
            MIN_MESSAGES_THRESHOLD=10,
            FILTER_BOT_MESSAGES=True,
            OUTPUT_FORMAT="image,html",
            REPORT_TEMPLATE="ATRI",
            ENABLE_ANALYSIS_REPLY=False,
            SHOW_REPORT_CAPTION=True,
            DEBUG_MODE=False,
            AUTO_ANALYSIS_TIME="22:30,08:00",
            SCHEDULED_GROUP_LIST_MODE="whitelist",
            SCHEDULED_GROUP_LIST="1",
            INCREMENTAL_GROUP_LIST_MODE="inherit",
            INCREMENTAL_GROUP_LIST="",
            INCREMENTAL_MIN_MESSAGES=100,
            INCREMENTAL_REPORT_IMMEDIATELY=False,
            ENABLE_DAILY_COMIC=True,
            ENABLE_AUTO_DAILY_COMIC=False,
            COMIC_GROUP_LIST_MODE="inherit",
            COMIC_GROUP_LIST="",
            CORE_CONFIG_JSON='{"html":{"html_base_url":"https://example.com","html_only_url":true}}',
        )
        merged = overlay_na_config(load_schema_defaults(), cfg)
        self.assertEqual(merged["llm"]["llm_provider_id"], "my-chat")
        self.assertEqual(merged["basic"]["report_template"], "ATRI")
        self.assertEqual(merged["basic"]["output_format"], ["image", "html"])
        self.assertEqual(merged["auto_analysis"]["auto_analysis_time"], ["22:30", "08:00"])
        self.assertTrue(merged["daily_comic"]["enable_daily_comic"])
        self.assertIn("topic_prompt", merged["prompts"]["topic_analysis_prompts"])
        self.assertEqual(merged["html"]["html_base_url"], "https://example.com")
        self.assertTrue(merged["html"]["html_only_url"])

    def test_overlay_keeps_default_html_when_json_omitted(self) -> None:
        cfg = SimpleNamespace(CORE_CONFIG_JSON="")
        merged = overlay_na_config(load_schema_defaults(), cfg)
        self.assertEqual(merged["html"]["html_base_url"], "")
        self.assertFalse(merged["html"]["html_only_url"])

    def test_overlay_exposes_original_schema_options(self) -> None:
        cfg = SimpleNamespace(
            REPORT_TEMPLATE="ATRI",
            T2I_R1_TYPE="jpeg",
            T2I_FONT_SOURCE="Mainland",
            T2I_MAINLAND_GOOGLE_FONTS="https://fonts.loli.net",
            TOPIC_ANALYSIS_ENABLED=False,
            GOLDEN_QUOTE_ANALYSIS_ENABLED=True,
            KEEP_ORIGINAL_PERSONA=True,
            MAX_TOPICS=7,
            OUTPUT_FORMAT=["image", "html"],
            PROFILE_DISPLAY_MODE="sbti",
        )
        merged = overlay_na_config(load_schema_defaults(), cfg)
        self.assertEqual(merged["basic"]["report_template"], "ATRI")
        self.assertEqual(merged["t2i_rendering"]["t2i_r1_type"], "jpeg")
        self.assertEqual(merged["t2i_rendering"]["t2i_font_source"], "Mainland")
        self.assertFalse(merged["analysis_features"]["topic_analysis_enabled"])
        self.assertTrue(merged["analysis_features"]["keep_original_persona"])
        self.assertEqual(merged["analysis_features"]["max_topics"], 7)
        self.assertEqual(merged["basic"]["output_format"], ["image", "html"])
        self.assertEqual(merged["basic"]["profile_display_mode"], "sbti")

    def test_schema_covers_original_dropdowns_and_hints(self) -> None:
        specs = {spec.na_name: spec for spec in iter_field_specs()}
        self.assertIn("REPORT_TEMPLATE", specs)
        self.assertIn("ATRI", specs["REPORT_TEMPLATE"].options)
        self.assertIn("scrapbook", specs["REPORT_TEMPLATE"].options)
        self.assertTrue(specs["REPORT_TEMPLATE"].description)
        self.assertEqual(specs["T2I_R1_TYPE"].options, ("jpeg", "png"))
        self.assertEqual(specs["T2I_FONT_SOURCE"].options, ("Mainland", "Overseas"))
        self.assertTrue(specs["TOPIC_ANALYSIS_ENABLED"].description)
        self.assertTrue(specs["KEEP_ORIGINAL_PERSONA"].description)
        self.assertTrue(specs["MODEL_GROUP"].ref_model_groups)
        self.assertTrue(specs["PLUGIN_SPECIFIC_PERSONA_ID"].ref_presets)
        self.assertTrue(specs["TOPIC_PROMPT"].is_textarea)
        self.assertGreaterEqual(len(specs), 80)

    def test_draw_model_group_is_na_native_and_astrbot_backends_hidden(self) -> None:
        from na_schema import extra_na_specs

        extras = {spec.na_name: spec for spec in extra_na_specs()}
        self.assertEqual(extras["DRAW_MODEL_GROUP"].model_type, "draw")
        self.assertTrue(extras["DRAW_MODEL_GROUP"].ref_model_groups)
        self.assertEqual(extras["DRAW_MODEL_GROUP"].path, ("daily_comic", "draw_model_group"))
        self.assertEqual(extras["DRAW_MODEL_MODE"].options, ("聊天模式", "图像生成"))

        specs = {spec.na_name: spec for spec in iter_field_specs()}
        self.assertTrue(specs["DRAWING_BACKEND"].is_hidden)
        self.assertTrue(specs["DRAWING_PROVIDER_OVERRIDES"].is_hidden)
        self.assertTrue(specs["DRAWING_EXTERNAL_FALLBACK"].is_hidden)

    def test_overlay_maps_draw_model_group(self) -> None:
        cfg = SimpleNamespace(
            DRAW_MODEL_GROUP="default-draw",
            DRAW_MODEL_MODE="图像生成",
            CORE_CONFIG_JSON="",
        )
        merged = overlay_na_config(load_schema_defaults(), cfg)
        self.assertEqual(merged["daily_comic"]["draw_model_group"], "default-draw")
        self.assertEqual(merged["daily_comic"]["draw_model_mode"], "图像生成")

    def test_draw_provider_from_group_chat_and_images(self) -> None:
        from na_draw import draw_provider_from_group

        group = SimpleNamespace(
            API_KEY="secret-key",
            BASE_URL="https://api.example.com/v1",
            CHAT_MODEL="gemini-3-pro-image-preview",
            CHAT_PROXY="",
        )
        chat = draw_provider_from_group(group, "default-draw", "聊天模式")
        self.assertIsNotNone(chat)
        self.assertEqual(chat["api_protocol"], "chat")
        self.assertEqual(chat["model"], "gemini-3-pro-image-preview")
        self.assertEqual(chat["_priority"], 1000)
        images = draw_provider_from_group(group, "default-draw", "图像生成")
        self.assertEqual(images["api_protocol"], "images")
        self.assertIsNone(
            draw_provider_from_group(SimpleNamespace(API_KEY="", BASE_URL="x", CHAT_MODEL="m"), "x", "聊天模式")
        )

    def test_list_fields_accept_legacy_strings(self) -> None:
        from pydantic import Field, create_model

        specs = {spec.na_name: spec for spec in iter_field_specs()}
        model = create_model(
            "LegacyLists",
            GROUP_LIST=(specs["GROUP_LIST"].python_type, Field(default_factory=list)),
            OUTPUT_FORMAT=(specs["OUTPUT_FORMAT"].python_type, Field(default_factory=lambda: ["image"])),
            AUTO_ANALYSIS_TIME=(specs["AUTO_ANALYSIS_TIME"].python_type, Field(default_factory=lambda: ["23:00"])),
        )
        parsed = model(
            GROUP_LIST="",
            OUTPUT_FORMAT="image",
            AUTO_ANALYSIS_TIME="23:00",
        )
        self.assertEqual(parsed.GROUP_LIST, [])
        self.assertEqual(parsed.OUTPUT_FORMAT, ["image"])
        self.assertEqual(parsed.AUTO_ANALYSIS_TIME, ["23:00"])
        parsed2 = model(GROUP_LIST="1079396715", OUTPUT_FORMAT="image,html", AUTO_ANALYSIS_TIME="22:30,08:00")
        self.assertEqual(parsed2.GROUP_LIST, ["1079396715"])
        self.assertEqual(parsed2.OUTPUT_FORMAT, ["image", "html"])
        self.assertEqual(parsed2.AUTO_ANALYSIS_TIME, ["22:30", "08:00"])

    def test_chat_completions_url_normalizes_base(self) -> None:
        self.assertEqual(
            chat_completions_url("https://api.example.com/v1"),
            "https://api.example.com/v1/chat/completions",
        )
        self.assertEqual(
            chat_completions_url("https://api.example.com/v1/chat/completions"),
            "https://api.example.com/v1/chat/completions",
        )
        self.assertEqual(
            chat_completions_url("https://api.example.com"),
            "https://api.example.com/v1/chat/completions",
        )


class T2IDefaultTests(unittest.TestCase):
    def test_empty_url_falls_back_to_official_endpoint(self) -> None:
        url, path = resolve_t2i_endpoint("", "")
        self.assertEqual(url, DEFAULT_T2I_API_URL)
        self.assertEqual(path, DEFAULT_T2I_API_PATH)

    def test_custom_url_is_kept(self) -> None:
        url, path = resolve_t2i_endpoint(" https://t2i.vercel.ciallo.de5.net ", "/generate")
        self.assertEqual(url, "https://t2i.vercel.ciallo.de5.net")
        self.assertEqual(path, "/generate")


class NestedConfigTests(unittest.TestCase):
    def test_nested_config_save(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested_config.json"
            cfg = NestedConfig({"basic": {"group_list": []}}, persist_path=path)
            cfg["basic"]["group_list"] = ["1"]
            cfg.save_config()
            self.assertIn('"1"', path.read_text(encoding="utf-8"))


class BotProxyTests(unittest.TestCase):
    def test_bot_call_proxy_maps_call_action(self) -> None:
        class FakeBot:
            async def call_api(self, action: str, **kwargs):
                return {"action": action, **kwargs}

        proxy = BotCallProxy(FakeBot())

        async def _run():
            return await proxy.call_action("get_group_msg_history", group_id="1")

        result = asyncio.run(_run())
        self.assertEqual(result["action"], "get_group_msg_history")
        self.assertEqual(result["group_id"], "1")

    def test_bot_call_proxy_ignores_getattr_call_action(self) -> None:
        class FakeNoneBot:
            def __getattr__(self, name: str):
                async def _fake(*args, **kwargs):
                    raise AssertionError(f"should not call getattr {name}")

                return _fake

            async def call_api(self, api: str, **kwargs):
                return {"api": api, **kwargs}

        proxy = BotCallProxy(FakeNoneBot())

        async def _run():
            return await proxy.call_action("get_group_info", group_id=2)

        result = asyncio.run(_run())
        self.assertEqual(result["api"], "get_group_info")
        self.assertEqual(result["group_id"], 2)


class FactoryTests(unittest.TestCase):
    def test_onebot_v11_alias_is_registered(self) -> None:
        from src.infrastructure.platform.factory import PlatformAdapterFactory

        self.assertTrue(PlatformAdapterFactory.is_supported("onebot"))
        self.assertTrue(PlatformAdapterFactory.is_supported("onebot_v11"))
        self.assertTrue(PlatformAdapterFactory.is_supported("aiocqhttp"))


class LocalHistoryTests(unittest.TestCase):
    def test_local_history_insert_and_get(self) -> None:
        with TemporaryDirectory() as tmp:
            store = LocalMessageHistoryManager(Path(tmp) / "history")

            async def _run():
                await store.insert(
                    "telegram",
                    "100",
                    {"type": "user", "message": [{"type": "plain", "text": "hi"}]},
                    "u1",
                    "alice",
                )
                await store.insert(
                    "telegram",
                    "100",
                    {"type": "user", "message": [{"type": "plain", "text": "yo"}]},
                    "u2",
                    "bob",
                )
                return await store.get("telegram", "100", page=1, page_size=10)

            page = asyncio.run(_run())
            self.assertEqual(len(page), 2)
            self.assertEqual(page[0].sender_name, "bob")
            self.assertEqual(page[0].id, 2)
            self.assertEqual(page[1].sender_name, "alice")


class ConfigManagerTests(unittest.TestCase):
    def test_config_manager_reads_overlay(self) -> None:
        from astrbot.api.star import set_data_dir_factory
        from src.infrastructure.config.config_manager import ConfigManager

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            set_data_dir_factory(lambda _name: tmp_path)
            cfg = SimpleNamespace(
                MODEL_GROUP="default",
                GROUP_LIST_MODE="whitelist",
                GROUP_LIST="123456",
                ANALYSIS_DAYS=1,
                MAX_MESSAGES=1000,
                MIN_MESSAGES_THRESHOLD=200,
                FILTER_BOT_MESSAGES=True,
                OUTPUT_FORMAT="image",
                REPORT_TEMPLATE="scrapbook",
                ENABLE_ANALYSIS_REPLY=False,
                SHOW_REPORT_CAPTION=True,
                DEBUG_MODE=False,
                AUTO_ANALYSIS_TIME="23:00",
                SCHEDULED_GROUP_LIST_MODE="whitelist",
                SCHEDULED_GROUP_LIST="123456",
                INCREMENTAL_GROUP_LIST_MODE="whitelist",
                INCREMENTAL_GROUP_LIST="123456",
                INCREMENTAL_MIN_MESSAGES=300,
                INCREMENTAL_REPORT_IMMEDIATELY=False,
                ENABLE_DAILY_COMIC=False,
                ENABLE_AUTO_DAILY_COMIC=True,
                COMIC_GROUP_LIST_MODE="inherit",
                COMIC_GROUP_LIST="",
                CORE_CONFIG_JSON="",
            )
            nested = NestedConfig(
                overlay_na_config(load_schema_defaults(), cfg),
                persist_path=tmp_path / "nested.json",
            )
            manager = ConfigManager(nested)
            self.assertTrue(manager.is_group_allowed("123456"))
            self.assertEqual(manager.get_report_template(), "scrapbook")
            self.assertTrue(manager.get_incremental_enabled())
            self.assertEqual(manager.get_drawing_backend(), "builtin")
            self.assertEqual(manager.get_draw_model_group_name(), "default-draw")
            self.assertEqual(manager.get_draw_model_mode(), "聊天模式")

    def test_replace_from_applies_live_atri_overlay(self) -> None:
        from astrbot.api.star import set_data_dir_factory
        from src.infrastructure.config.config_manager import ConfigManager
        from src.shared.constants import PLUGIN_REPO_LABEL, PLUGIN_REPO_URL

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            set_data_dir_factory(lambda _name: tmp_path)
            stale = NestedConfig({"basic": {"report_template": "scrapbook"}})
            manager = ConfigManager(stale)
            self.assertEqual(manager.get_report_template(), "scrapbook")
            live = SimpleNamespace(
                REPORT_TEMPLATE="ATRI",
                CORE_CONFIG_JSON="",
            )
            updated = overlay_na_config(load_schema_defaults(), live)
            stale.replace_from(updated)
            self.assertEqual(manager.get_report_template(), "ATRI")
            self.assertEqual(PLUGIN_REPO_LABEL, "Akiyo-dayo/nekro-plugin-group-daily-analysis")
            self.assertIn("Akiyo-dayo", PLUGIN_REPO_URL)

    def test_atri_footer_uses_plugin_repo_placeholders(self) -> None:
        template = (
            ROOT
            / "src"
            / "infrastructure"
            / "reporting"
            / "templates"
            / "ATRI"
            / "image_template.html"
        ).read_text(encoding="utf-8")
        self.assertIn("{{ plugin_repo_url }}", template)
        self.assertIn("{{ plugin_repo_label }}", template)
        self.assertNotIn("SXP-Simon/astrbot_plugin_qq_group_daily_analysis", template)
        self.assertIn("Template by Liangyu-G", template)


if __name__ == "__main__":
    unittest.main()
