from __future__ import annotations

from typing import Any

from src.utils.logger import logger


class BotCallProxy:
    """让 NA OneBot Bot 兼容原插件的 call_action 接口。"""

    def __init__(self, bot: Any) -> None:
        self._bot = bot

    async def call_action(self, action: str, **kwargs: Any) -> Any:
        # nonebot Bot 会用 __getattr__ 把任意名字伪装成 API，不能用 hasattr(bot, "call_action")。
        native_api = getattr(type(self._bot), "call_api", None)
        if callable(native_api):
            return await self._bot.call_api(action, **kwargs)
        native_action = getattr(type(self._bot), "call_action", None)
        if callable(native_action):
            return await self._bot.call_action(action, **kwargs)
        call_api = getattr(self._bot, "call_api", None)
        if callable(call_api):
            return await call_api(action, **kwargs)
        raise TypeError(f"{type(self._bot).__name__} 没有 call_api/call_action")

    def __getattr__(self, name: str) -> Any:
        return getattr(self._bot, name)


def bind_platform_bots(bot_manager: Any, chat_key: str | None = None) -> None:
    """把 NA 当前已连接的协议端注入原 BotManager。"""
    _bind_onebot(bot_manager, chat_key)
    _bind_optional(bot_manager, "discord", _get_discord_bot, "discord")
    _bind_optional(bot_manager, "telegram", _get_telegram_bot, "telegram")
    _bind_optional(bot_manager, "qqbot_openclaw", _get_qq_official_bot, "qq_official")
    _bind_optional(bot_manager, "qq_official", _get_qq_official_bot, "qq_official")


def _is_onebot_v11_bot(instance: Any) -> bool:
    module = type(instance).__module__.lower()
    adapter = getattr(instance, "adapter", None)
    adapter_name = str(getattr(adapter, "name", "") or type(adapter).__name__).lower()
    if any(token in module or token in adapter_name for token in ("minecraft", "discord", "telegram", "feishu", "lark")):
        return False
    try:
        from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot

        if isinstance(instance, OneBotV11Bot):
            return True
    except Exception:
        pass
    return "onebot" in module or "onebot" in adapter_name


def _list_onebot_bots() -> list[tuple[str, Any]]:
    """不依赖事件上下文，直接列出已连接的 OneBot V11 实例。"""
    try:
        from nonebot import get_bots

        bots = get_bots() or {}
    except Exception as exc:
        logger.debug(f"nonebot.get_bots 不可用: {exc}")
        return []

    found: list[tuple[str, Any]] = []
    for key, instance in bots.items():
        if _is_onebot_v11_bot(instance):
            found.append((str(key), instance))
    return found


def _resolve_onebot_bot(chat_key: str | None = None) -> Any | None:
    onebots = _list_onebot_bots()
    if chat_key:
        for key, bot in onebots:
            self_id = str(getattr(bot, "self_id", "") or key)
            if self_id and self_id in chat_key:
                return bot
    numeric = [
        (key, bot)
        for key, bot in onebots
        if str(getattr(bot, "self_id", "") or key).isdigit()
    ]
    if len(numeric) == 1:
        return numeric[0][1]
    if len(onebots) == 1:
        return onebots[0][1]
    if len(numeric) > 1:
        logger.warning(
            "检测到多个 OneBot QQ 连接 %s，未匹配 chat_key=%s，使用第一个 QQ 号",
            [key for key, _ in numeric],
            chat_key,
        )
        return numeric[0][1]
    if onebots:
        logger.warning(
            "检测到 OneBot 连接 %s，但无法按 QQ 号筛选，chat_key=%s",
            [key for key, _ in onebots],
            chat_key,
        )
        return onebots[0][1]
    try:
        from nekro_agent.adapters.onebot_v11.core.bot import get_bot

        return get_bot()
    except Exception as exc:
        logger.warning("当前没有可用的 OneBot 实例: %s", exc)
        return None


def _bind_onebot(bot_manager: Any, chat_key: str | None = None) -> None:
    bot = _resolve_onebot_bot(chat_key)
    if bot is None:
        return
    proxy = BotCallProxy(bot)
    for platform_id in ("onebot_v11", "onebot", "aiocqhttp"):
        bot_manager.set_bot_instance(
            proxy, platform_id=platform_id, platform_name="onebot"
        )
    self_id = getattr(bot, "self_id", None)
    if self_id:
        bot_manager.set_bot_self_ids([str(self_id)])
    logger.info("已绑定 OneBot 实例 self_id=%s chat_key=%s", self_id, chat_key)


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
