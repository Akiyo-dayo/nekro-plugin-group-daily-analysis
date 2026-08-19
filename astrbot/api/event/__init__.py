from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from .filter import PermissionType, filter


class MessageChain:
    def __init__(self, chain: list[Any] | None = None) -> None:
        self.chain = chain or []


class AstrMessageEvent:
    """将 NA ChatMessage 适配为原插件事件接口。"""

    def __init__(
        self,
        *,
        sender_id: str,
        sender_name: str,
        group_id: str,
        platform_id: str,
        platform_name: str,
        message_str: str,
        message_obj: Any = None,
        unified_msg_origin: str = "",
        message_id: str = "",
    ) -> None:
        self._sender_id = sender_id
        self._sender_name = sender_name
        self._group_id = group_id
        self._platform_id = platform_id
        self._platform_name = platform_name
        self.message_str = message_str
        self.message_obj = message_obj or SimpleNamespace(message=[])
        self.unified_msg_origin = unified_msg_origin
        self.message_id = message_id
        self.bot = None
        self._self_id = ""

    def get_sender_id(self) -> str:
        return self._sender_id

    def get_sender_name(self) -> str:
        return self._sender_name

    def get_group_id(self) -> str:
        return self._group_id

    def get_platform_id(self) -> str:
        return self._platform_id

    def get_platform_name(self) -> str:
        return self._platform_name

    def get_self_id(self) -> str:
        return self._self_id

    def should_call_llm(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def plain_result(self, text: str) -> str:
        return text

    def chain_result(self, chain: list[Any]) -> list[Any]:
        return chain
