from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

from astrbot.api import logger as astrbot_logger
from astrbot.api.star import StarTools, set_data_dir_factory
from bot_bridge import bind_platform_bots
from cron import CronManager
from html_render import HtmlRenderService
from llm_bridge import NAContext
from local_history import LocalMessageHistoryManager
from nested_config import NestedConfig, deep_merge, load_schema_defaults
from overlay_config import overlay_na_config
from src.application.commands.template_command_service import TemplateCommandService
from src.application.services.analysis_application_service import (
    AnalysisApplicationService,
)
from src.application.services.comic_application_service import ComicApplicationService
from src.application.services.message_processing_service import MessageProcessingService
from src.domain.services.analysis_domain_service import AnalysisDomainService
from src.domain.services.incremental_merge_service import IncrementalMergeService
from src.domain.services.statistics_service import StatisticsService
from src.infrastructure.analysis.llm_analyzer import LLMAnalyzer
from src.infrastructure.config.config_manager import ConfigManager
from src.infrastructure.drawing.drawing_client import DrawingClient
from src.infrastructure.messaging.message_sender import MessageSender
from src.infrastructure.persistence.history_manager import HistoryManager
from src.infrastructure.persistence.incremental_store import IncrementalStore
from src.infrastructure.persistence.platform_group_registry import PlatformGroupRegistry
from src.infrastructure.platform.bot_manager import BotManager
from src.infrastructure.platform.template_preview import (
    TelegramTemplatePreviewHandler,
    TemplatePreviewRouter,
)
from src.infrastructure.reporting.generators import ReportGenerator
from src.infrastructure.scheduler.auto_scheduler import AutoScheduler
from src.infrastructure.visualization.activity_charts import ActivityVisualizer
from src.shared.constants import PLUGIN_NAME
from src.shared.trace_context import TraceContext, TraceLogFilter
from src.utils.logger import logger
from src.utils.resilience import GlobalRateLimiter

_PLUGIN_ROOT = Path(__file__).resolve().parent
_runtime: PluginRuntime | None = None


def _plugin_data_dir(na_plugin: Any) -> Path:
    getter = getattr(na_plugin, "get_plugin_data_dir", None)
    if callable(getter):
        return Path(getter())
    return Path(na_plugin.get_plugin_path())


class PluginRuntime:
    """把原 AstrBot Star 主类接到 NA 生命周期上。"""

    def __init__(self, na_plugin: Any, na_config: Any) -> None:
        self.na_plugin = na_plugin
        self.na_config = na_config
        self._terminating = False
        self._initialized = False
        self._init_lock = asyncio.Lock()
        self._background_tasks: set[asyncio.Task] = set()
        self._comic_group_tasks: dict[str, asyncio.Task] = {}

        data_dir = _plugin_data_dir(na_plugin)
        data_dir.mkdir(parents=True, exist_ok=True)
        set_data_dir_factory(lambda _name: data_dir)

        persist_path = data_dir / "nested_config.json"
        persisted: dict[str, Any] = {}
        if persist_path.exists():
            try:
                loaded = json.loads(persist_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    persisted = loaded
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(f"读取持久化嵌套配置失败: {exc}")

        try:
            nested = overlay_na_config(load_schema_defaults(), na_config)
        except Exception as exc:
            logger.error(f"叠加 NA 配置失败，将使用默认配置: {exc}", exc_info=True)
            nested = load_schema_defaults()
        nested = deep_merge(nested, persisted)
        self.nested_config = NestedConfig(nested, persist_path=persist_path)

        self.html_render_service = HtmlRenderService(
            getattr(na_config, "T2I_API_URL", ""),
            getattr(na_config, "T2I_API_PATH", "/generate"),
        )
        self.cron_manager = CronManager()
        self.context = NAContext(
            default_group=str(getattr(na_config, "MODEL_GROUP", "default") or "default"),
            cron_manager=self.cron_manager,
        )
        self.context.message_history_manager = LocalMessageHistoryManager(
            data_dir / "local_history"
        )
        self.context.platform_manager = None

        self.config_manager = ConfigManager(self.nested_config)
        self.bot_manager = BotManager(self.config_manager)
        self.bot_manager.set_context(self.context)
        self.bot_manager.set_plugin_instance(self)
        self.history_manager = HistoryManager(self)

        plugin_data_dir = StarTools.get_data_dir(PLUGIN_NAME)
        self.report_generator = ReportGenerator(self.config_manager, plugin_data_dir)
        self.platform_group_registry = PlatformGroupRegistry(self)
        activity_visualizer = ActivityVisualizer()
        self.statistics_service = StatisticsService(activity_visualizer)
        self.analysis_domain_service = AnalysisDomainService()
        self.llm_analyzer = LLMAnalyzer(self.context, self.config_manager)
        self.incremental_store = IncrementalStore(self)
        self.incremental_merge_service = IncrementalMergeService()
        self.analysis_service = AnalysisApplicationService(
            self.config_manager,
            self.bot_manager,
            self.history_manager,
            self.report_generator,
            self.llm_analyzer,
            self.statistics_service,
            self.analysis_domain_service,
            incremental_store=self.incremental_store,
            incremental_merge_service=self.incremental_merge_service,
        )
        self.drawing_client = DrawingClient(self.config_manager)
        self.comic_service = ComicApplicationService(
            self.llm_analyzer,
            self.drawing_client,
            self.config_manager,
            plugin_data_dir,
            context=self.context,
        )
        self.message_processing_service = MessageProcessingService(
            self.context, self.platform_group_registry
        )
        self._comic_semaphore = asyncio.Semaphore(
            max(1, self.config_manager.get_t2i_max_concurrent())
        )
        self.template_command_service = TemplateCommandService(plugin_root=str(_PLUGIN_ROOT))
        self.telegram_template_preview_handler = TelegramTemplatePreviewHandler(
            config_manager=self.config_manager,
            template_service=self.template_command_service,
        )
        self.template_preview_router = TemplatePreviewRouter(
            handlers=[self.telegram_template_preview_handler]
        )
        self.message_sender = MessageSender(self.bot_manager, self.config_manager)
        self.auto_scheduler = AutoScheduler(
            self.config_manager,
            self.analysis_service,
            self.bot_manager,
            self.report_generator,
            self.html_render_service,
            plugin_instance=self,
        )
        GlobalRateLimiter.get_instance(self.config_manager.get_llm_max_concurrent())

    async def html_render(self, *args: Any, **kwargs: Any) -> Any:
        return await self.html_render_service(*args, **kwargs)

    async def put_kv_data(self, key: str, value: Any) -> None:
        encoded = json.dumps(value, ensure_ascii=False, default=str)
        await self.na_plugin.store.set(chat_key="", store_key=str(key), value=encoded)

    async def get_kv_data(self, key: str, default: Any = None) -> Any:
        raw = await self.na_plugin.store.get(chat_key="", store_key=str(key))
        if raw is None or raw == "":
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    async def start(self) -> None:
        async with self._init_lock:
            if self._terminating:
                return
            self.html_render_service.configure(
                getattr(self.na_config, "T2I_API_URL", ""),
                getattr(self.na_config, "T2I_API_PATH", "/generate"),
            )
            self.context.refresh_providers(
                str(getattr(self.na_config, "MODEL_GROUP", "default") or "default")
            )
            if not self._initialized:
                trace_filter = TraceLogFilter()
                if not any(isinstance(item, TraceLogFilter) for item in astrbot_logger.filters):
                    astrbot_logger.addFilter(trace_filter)
                try:
                    self.config_manager.upgrade_prompt_templates()
                except Exception as exc:
                    logger.warning(f"升级 prompt 模板失败：{exc}")
                try:
                    self.config_manager.migrate_legacy_configs()
                except Exception as exc:
                    logger.warning(f"迁移旧版配置失败：{exc}")
            bind_platform_bots(self.bot_manager)
            await self.bot_manager.initialize_from_config()
            try:
                await self.template_preview_router.ensure_handlers_registered(self.context)
            except Exception as exc:
                logger.debug(f"模板预览处理器注册跳过: {exc}")
            self.cron_manager.start()
            if self.auto_scheduler:
                self.auto_scheduler.schedule_jobs(self.context)
                await self.auto_scheduler.start_incremental_trigger()
            self._initialized = True
            logger.info("群分析插件已在 NekroAgent 中初始化")

    async def stop(self) -> None:
        if self._terminating:
            return
        self._terminating = True
        logger.info("开始清理群日常分析插件资源...")
        if self._background_tasks:
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
            try:
                await asyncio.wait(list(self._background_tasks), timeout=3.0)
            except Exception:
                pass
            self._background_tasks.clear()
        if self.auto_scheduler:
            await self.auto_scheduler.shutdown(self.context)
        if self.template_preview_router:
            await self.template_preview_router.unregister_handlers()
        if self.report_generator:
            await self.report_generator.close()
        await self.cron_manager.shutdown()
        logger.info("群日常分析插件资源清理完成")

    def bind_bots(self, chat_key: str | None = None) -> None:
        bind_platform_bots(self.bot_manager, chat_key)

    def first_self_id(self) -> str:
        ids = self.bot_manager._bot_self_ids
        return str(ids[0]) if ids else ""

    async def get_telegram_seen_group_ids(
        self, platform_id: str | None = None
    ) -> list[str]:
        return await self.platform_group_registry.get_all_group_ids(platform_id)

    async def get_seen_group_ids(self, platform_id: str | None = None) -> list[str]:
        return await self.platform_group_registry.get_all_group_ids(platform_id)

    async def refresh_incremental_target_states(self) -> None:
        incremental_trigger = self.auto_scheduler.incremental_trigger
        if incremental_trigger:
            await incremental_trigger.refresh_target_states()

    def track(self, task: asyncio.Task) -> asyncio.Task:
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def send_analysis_report(self, result: dict[str, Any], chat_key: str) -> str:
        if self._terminating or not self.config_manager:
            return "插件正在关闭，停止发送报告"
        group_id = result["group_id"]
        platform_id = result["platform_id"]
        analysis_result = result["analysis_result"]
        adapter = result["adapter"]
        self.try_trigger_comic_generation(group_id, platform_id, analysis_result)
        output_format = self.config_manager.get_output_format()[0]
        is_qq_official = adapter.get_platform_name() in {
            "qq_official",
            "qq_official_webhook",
        }

        async def avatar_url_getter(user_id: str) -> str | None:
            return await adapter.get_user_avatar_url(user_id)

        async def nickname_getter(user_id: str) -> str | None:
            try:
                member = await adapter.get_member_info(group_id, user_id)
                if member:
                    return member.card or member.nickname
            except Exception:
                pass
            return None

        if output_format == "image":
            image_url, _html_content = await self.report_generator.generate_image_report(
                analysis_result,
                group_id,
                self.html_render,
                avatar_url_getter=avatar_url_getter,
                nickname_getter=nickname_getter,
                avatar_cache_namespace=platform_id,
                allow_alphanumeric_user_ids=is_qq_official,
            )
            if image_url:
                caption = (
                    TraceContext.make_report_caption()
                    if self.config_manager.get_show_report_caption()
                    else ""
                )
                sent = await adapter.send_image(group_id, image_url, caption=caption)
                if sent:
                    await self.try_upload_image(group_id, image_url, platform_id)
                    return "image_sent"
            logger.warning(f"图片报告发送失败，正在发送文本回退报告。群: {group_id}")
            await self.send_text_reports(group_id, analysis_result, is_qq_official, adapter)
            return "text_fallback"

        if output_format == "html":
            html_path, _json_path = await self.report_generator.generate_html_report(
                analysis_result,
                group_id,
                avatar_url_getter=avatar_url_getter,
                nickname_getter=nickname_getter,
                avatar_cache_namespace=platform_id,
                allow_alphanumeric_user_ids=is_qq_official,
            )
            if not html_path:
                return "html_failed"
            is_only_url = self.config_manager.get_html_only_url()
            base_url = self.config_manager.get_html_base_url()
            if is_only_url and base_url and base_url.strip():
                html_output_dir = self.config_manager.get_html_output_dir() or os.path.join(
                    str(StarTools.get_data_dir(PLUGIN_NAME)),
                    "self_hosted_html_reports",
                )
                rel_path = os.path.relpath(html_path, html_output_dir)
                encoded = quote(rel_path.replace(os.sep, "/").lstrip("/"), safe="/")
                report_url = f"{base_url.rstrip('/')}/{encoded}"
                await adapter.send_text(group_id, f"📊 今日群聊分析报告已生成：\n{report_url}")
                return report_url
            caption = self.report_generator.build_html_caption(html_path)
            sent = await self.message_sender.send_file(
                group_id,
                html_path,
                caption=caption,
                platform_id=platform_id,
            )
            if not sent:
                try:
                    from nekro_agent.api import message as na_message

                    await na_message.send_file(chat_key, html_path, None)
                    if caption:
                        await na_message.send_text(chat_key, caption, None)
                except Exception as exc:
                    logger.warning(f"HTML 文件发送失败: {exc}")
                    return "html_send_failed"
            return "html_sent"

        await self.send_text_reports(group_id, analysis_result, is_qq_official, adapter)
        return "text_sent"

    async def generate_text_reports(
        self, analysis_result: dict, use_qq_official_markdown: bool
    ) -> tuple[str, str | None]:
        if use_qq_official_markdown:
            return await self.report_generator.generate_qq_official_markdown_report(
                analysis_result, self.html_render
            )
        return self.report_generator.generate_text_report(analysis_result), None

    async def send_text_reports(
        self,
        group_id: str,
        analysis_result: dict,
        use_qq_official_markdown: bool,
        adapter,
    ) -> bool:
        text_report, fallback = await self.generate_text_reports(
            analysis_result, use_qq_official_markdown
        )
        if use_qq_official_markdown:
            return await adapter.send_text_report(
                group_id, text_report, fallback_content=fallback
            )
        return await adapter.send_text_report(group_id, text_report)

    def try_trigger_comic_generation(
        self,
        group_id: str,
        platform_id: str | None,
        analysis_result: dict,
        *,
        require_auto_enabled: bool = True,
    ) -> str:
        if self._terminating:
            return "terminating"
        if not self.config_manager.get_enable_daily_comic():
            return "disabled"
        auto_comic_enabled = getattr(self.config_manager, "get_enable_auto_daily_comic", None)
        if require_auto_enabled and callable(auto_comic_enabled) and not auto_comic_enabled():
            return "auto_disabled"
        umo = f"{platform_id}:GroupMessage:{group_id}" if platform_id else group_id
        comic_allowed = getattr(self.config_manager, "is_comic_group_allowed", None)
        inherit_allowed = True if require_auto_enabled else None
        if callable(comic_allowed) and not comic_allowed(umo, inherit_allowed):
            return "blocked"
        topics = analysis_result.get("topics", [])
        statistics = analysis_result.get("statistics")
        if not topics and statistics:
            topics = getattr(statistics, "topics", [])
        comic_topics = []
        for topic in topics if isinstance(topics, list) else []:
            title = (
                topic.get("topic", "")
                if isinstance(topic, dict)
                else getattr(topic, "topic", "")
            )
            detail = (
                topic.get("detail", "")
                if isinstance(topic, dict)
                else getattr(topic, "detail", "")
            )
            if str(title).strip():
                comic_topics.append(
                    {"topic": str(title).strip(), "detail": str(detail).strip()}
                )
        if not comic_topics:
            return "no_topics"
        task_key = f"{platform_id or 'default'}:{group_id}"
        existing = self._comic_group_tasks.get(task_key)
        if existing and not existing.done():
            return "duplicate"
        task = asyncio.create_task(
            self._trigger_comic_generation(comic_topics, group_id, platform_id, umo)
        )
        self._comic_group_tasks[task_key] = task
        self.track(task)
        task.add_done_callback(
            lambda completed: (
                self._comic_group_tasks.pop(task_key, None)
                if self._comic_group_tasks.get(task_key) is completed
                else None
            )
        )
        return "started"

    @staticmethod
    def detect_image_ext(data: bytes) -> str:
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if data.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return ".webp"
        if data.startswith((b"GIF87a", b"GIF89a")):
            return ".gif"
        return ".png"

    async def _trigger_comic_generation(
        self,
        topics: list[dict],
        group_id: str,
        platform_id: str | None,
        umo: str,
    ) -> None:
        async with self._comic_semaphore:
            if self._terminating:
                return
            try:
                comic_bytes, fallback_url = await self.comic_service.generate_comic(
                    topics, group_id, umo
                )
                if comic_bytes:
                    import time

                    ext = self.detect_image_ext(comic_bytes)
                    comic_dir = StarTools.get_data_dir(PLUGIN_NAME) / "comic_cache"
                    comic_dir.mkdir(parents=True, exist_ok=True)
                    comic_file_path = str(
                        comic_dir / f"comic_{group_id}_{int(time.time())}{ext}"
                    )
                    with open(comic_file_path, "wb") as handle:
                        handle.write(comic_bytes)
                    try:
                        adapter = self.bot_manager.get_adapter(platform_id)
                        if adapter and hasattr(adapter, "send_image"):
                            await adapter.send_image(
                                group_id,
                                comic_file_path,
                                caption="✨ 今日群聊趣味漫画已生成！",
                            )
                        await self.try_upload_image(
                            group_id, comic_file_path, platform_id, is_comic=True
                        )
                    finally:
                        try:
                            os.remove(comic_file_path)
                        except OSError:
                            pass
                elif fallback_url:
                    adapter = self.bot_manager.get_adapter(platform_id)
                    if adapter and hasattr(adapter, "send_text"):
                        await adapter.send_text(
                            group_id,
                            f"✨ 今日群聊趣味漫画已生成，但图片下载失败，请点击链接查看：\n{fallback_url}",
                        )
            except Exception as exc:
                logger.error(f"群 {group_id} 生成/上传漫画时发生错误: {exc}", exc_info=True)

    async def try_upload_image(
        self,
        group_id: str,
        image_url: str,
        platform_id: str | None,
        is_comic: bool = False,
    ) -> None:
        import base64
        import re
        import tempfile
        from datetime import datetime

        if is_comic:
            enable_file = False
            enable_album = self.config_manager.get_enable_comic_album_upload()
        else:
            enable_file = self.config_manager.get_enable_group_file_upload()
            enable_album = self.config_manager.get_enable_group_album_upload()
        if not enable_file and not enable_album:
            return
        adapter = self.bot_manager.get_adapter(platform_id)
        if not adapter:
            return
        if enable_file and not hasattr(adapter, "upload_group_file_to_folder"):
            enable_file = False
        if enable_album and not hasattr(adapter, "upload_group_album"):
            enable_album = False
        if not enable_file and not enable_album:
            return
        now = datetime.now()
        filename_stem = f"群分析报告_{group_id}_{now.strftime('%Y-%m-%d')}_{now.strftime('%H%M')}"
        try:
            group_info = await adapter.get_group_info(group_id)
            if group_info and group_info.group_name:
                safe_name = re.sub(r'[\\/:*?"<>|]', "", group_info.group_name).strip()
                if safe_name:
                    filename_stem = f"群分析报告_{safe_name}_{now.strftime('%Y-%m-%d')}_{now.strftime('%H%M')}"
        except Exception:
            pass
        image_file = None
        created_temp = False
        try:
            data = None
            if image_url.startswith("base64://"):
                data = base64.b64decode(image_url[len("base64://") :])
            elif image_url.startswith("data:"):
                parts = image_url.split(",", 1)
                if len(parts) == 2:
                    data = base64.b64decode(parts[1])
            elif os.path.isfile(image_url):
                image_file = os.path.abspath(image_url)
            if is_comic:
                image_header = data
                if image_header is None and image_file:
                    with open(image_file, "rb") as stream:
                        image_header = stream.read(32)
                ext = self.detect_image_ext(image_header or b"")
            else:
                ext = (
                    ".jpg"
                    if (".jpg" in image_url.lower() or ".jpeg" in image_url.lower())
                    else ".png"
                )
            nice_filename = f"{filename_stem}{ext}"
            if data and not image_file:
                fd, image_file = tempfile.mkstemp(suffix=ext, prefix="group_report_")
                try:
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(data)
                    created_temp = True
                except Exception:
                    os.close(fd)
                    raise
            if not image_file:
                return
            if enable_file:
                try:
                    folder_name = self.config_manager.get_group_file_folder()
                    folder_id = None
                    if folder_name:
                        folder_id = await adapter.find_or_create_folder(group_id, folder_name)
                    await adapter.upload_group_file_to_folder(
                        group_id=group_id,
                        file_path=image_file,
                        folder_id=folder_id,
                        filename=nice_filename,
                    )
                except Exception as exc:
                    logger.warning(f"群文件上传失败 (群 {group_id}): {exc}")
            if enable_album:
                try:
                    album_name = (
                        self.config_manager.get_comic_album_name()
                        if is_comic
                        else self.config_manager.get_group_album_name()
                    )
                    strict_mode = self.config_manager.get_group_album_strict_mode()
                    if strict_mode and not album_name:
                        logger.info("相册严格模式开启且未设置相册名，跳过上传")
                    elif hasattr(adapter, "upload_group_album"):
                        await adapter.upload_group_album(
                            group_id,
                            image_file,
                            album_id=None,
                            album_name=album_name,
                            strict_mode=strict_mode,
                        )
                except Exception as exc:
                    logger.warning(f"群相册上传失败 (群 {group_id}): {exc}")
        except Exception as exc:
            logger.warning(f"图片上传处理异常: {exc}")
        finally:
            if created_temp and image_file and os.path.exists(image_file):
                try:
                    os.remove(image_file)
                except OSError:
                    pass


async def start_runtime(na_plugin: Any, na_config: Any) -> PluginRuntime:
    global _runtime
    if _runtime is None:
        _runtime = PluginRuntime(na_plugin, na_config)
    await _runtime.start()
    return _runtime


async def stop_runtime() -> None:
    global _runtime
    if _runtime is not None:
        await _runtime.stop()
        _runtime = None


def get_runtime() -> PluginRuntime:
    if _runtime is None:
        raise RuntimeError("群分析插件尚未初始化")
    return _runtime
