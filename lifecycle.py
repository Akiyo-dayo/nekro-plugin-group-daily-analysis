from __future__ import annotations

from chat_key import parse_chat_key
from events import chat_message_to_event
from nekro_agent.api.schemas import AgentCtx
from plugin import config, plugin
from runtime import get_runtime, start_runtime, stop_runtime
from src.utils.logger import logger


@plugin.mount_init_method()
async def init_plugin() -> None:
    await start_runtime(plugin, config)


@plugin.mount_cleanup_method()
async def cleanup_plugin() -> None:
    await stop_runtime()


@plugin.on_enabled()
async def on_plugin_enabled() -> None:
    await start_runtime(plugin, config)


@plugin.on_disabled()
async def on_plugin_disabled() -> None:
    await stop_runtime()


@plugin.mount_on_user_message()
async def on_user_message(_ctx: AgentCtx, message):
    try:
        runtime = get_runtime()
    except RuntimeError:
        return None
    parsed = parse_chat_key(getattr(message, "chat_key", "") or "")
    if not parsed.is_group:
        return None
    runtime.bind_bots()
    adapter = runtime.bot_manager.get_adapter(parsed.adapter_key)
    bot = runtime.bot_manager.get_bot_instance(parsed.adapter_key) or (
        adapter.bot if adapter is not None else None
    )
    event = chat_message_to_event(
        message,
        bot=bot,
        self_id=runtime.first_self_id(),
    )
    try:
        if parsed.platform_name in {
            "telegram",
            "qq_official",
            "qq_official_webhook",
        } or parsed.adapter_key in {"qqbot_openclaw", "telegram"}:
            stored = await runtime.message_processing_service.process_message(event)
            if stored and runtime.auto_scheduler:
                await runtime.auto_scheduler.record_incremental_message(event)
        elif runtime.auto_scheduler:
            await runtime.auto_scheduler.record_incremental_message(event)
    except (ValueError, RuntimeError) as exc:
        logger.debug(f"群消息未计入增量统计: {exc}")
    except Exception as exc:
        logger.warning(f"处理群消息失败: {exc}", exc_info=True)
    return None
