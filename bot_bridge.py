from __future__ import annotations

from typing import Any

from src.utils.logger import logger


class BotCallProxy:
    """让 NA OneBot Bot 兼容原插件的 call_action 接口。"""

    def __init__(self, bot: Any) -> None:
        self._bot = bot

    async def call_action(self, action: str, **kwargs: Any) -> Any:
        if hasattr(self._bot, "call_action"):
            return await self._bot.call_action(action, **kwargs)
        return await self._bot.call_api(action, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._bot, name)


def bind_platform_bots(bot_manager: Any) -> None:
    """把 NA 当前已连接的协议端注入原 BotManager。"""
    _bind_onebot(bot_manager)
    _bind_optional(bot_manager, "discord", _get_discord_bot, "discord")
    _bind_optional(bot_manager, "telegram", _get_telegram_bot, "telegram")
    _bind_optional(bot_manager, "qqbot_openclaw", _get_qq_official_bot, "qq_official")
    _bind_optional(bot_manager, "qq_official", _get_qq_official_bot, "qq_official")


def _bind_onebot(bot_manager: Any) -> None:
    try:
        from nekro_agent.adapters.onebot_v11.core.bot import get_bot

        bot = get_bot()
    except Exception as exc:
        logger.debug(f"当前没有可用的 OneBot 实例: {exc}")
        return
    proxy = BotCallProxy(bot)
    for platform_id in ("onebot_v11", "onebot", "aiocqhttp"):
        bot_manager.set_bot_instance(
            proxy, platform_id=platform_id, platform_name="onebot"
        )
    self_id = getattr(bot, "self_id", None)
    if self_id:
        bot_manager.set_bot_self_ids([str(self_id)])


def _bind_optional(bot_manager: Any, platform_id: str, getter, platform_name: str) -> None:
    try:
        bot = getter()
    except Exception as exc:
        logger.debug(f"当前没有可用的 {platform_name} 实例: {exc}")
        return
    if bot is None:
        return
    bot_manager.set_bot_instance(bot, platform_id=platform_id, platform_name=platform_name)


def _get_discord_bot() -> Any | None:
    try:
        from nekro_agent.adapters.discord.core.bot import get_bot as get_discord_bot

        return get_discord_bot()
    except Exception:
        return None


def _get_telegram_bot() -> Any | None:
    try:
        from nekro_agent.adapters.telegram.core.bot import get_bot as get_telegram_bot

        return get_telegram_bot()
    except Exception:
        return None


def _get_qq_official_bot() -> Any | None:
    for import_path in (
        "nekro_agent.adapters.qqbot_openclaw.core.bot",
        "nekro_agent.adapters.qq_official.core.bot",
    ):
        try:
            module = __import__(import_path, fromlist=["get_bot"])
            getter = getattr(module, "get_bot", None)
            if callable(getter):
                return getter()
        except Exception:
            continue
    return None
