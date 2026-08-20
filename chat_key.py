from __future__ import annotations

import re
from dataclasses import dataclass

_CHAT_KEY_RE = re.compile(r"^(?P<adapter>[^-]+)-(?P<kind>group|private)_(?P<chat_id>.+)$")
_AKIYO_ONEBOT_CHAT_KEY_RE = re.compile(
    r"^onebot_v11-(?P<instance_key>[a-z0-9_]{1,32})-"
    r"(?P<kind>group|private)_(?P<chat_id>.+)$"
)


@dataclass(frozen=True)
class ParsedChatKey:
    adapter_key: str
    kind: str
    chat_id: str
    instance_key: str = ""

    @property
    def is_group(self) -> bool:
        return self.kind == "group"

    @property
    def platform_name(self) -> str:
        if self.adapter_key in {"onebot_v11", "onebot"}:
            return "onebot"
        if self.adapter_key in {"qqbot_openclaw", "qq_official", "qq_official_webhook"}:
            return "qq_official"
        if self.adapter_key.startswith("discord"):
            return "discord"
        if self.adapter_key.startswith("telegram"):
            return "telegram"
        if self.adapter_key in {"feishu", "lark"}:
            return "lark"
        return self.adapter_key

    @property
    def umo(self) -> str:
        if self.platform_name == "onebot":
            prefix = "GroupMessage" if self.is_group else "FriendMessage"
            return f"onebot:{prefix}:{self.chat_id}"
        if self.platform_name == "discord":
            return f"discord:ChannelMessage:{self.chat_id}"
        if self.platform_name == "telegram":
            return f"telegram:GroupMessage:{self.chat_id}"
        return f"{self.adapter_key}:{self.kind}:{self.chat_id}"


def parse_chat_key(chat_key: str) -> ParsedChatKey:
    text = (chat_key or "").strip()
    akiyo_match = _AKIYO_ONEBOT_CHAT_KEY_RE.match(text)
    if akiyo_match:
        return ParsedChatKey(
            adapter_key="onebot_v11",
            kind=akiyo_match.group("kind"),
            chat_id=akiyo_match.group("chat_id"),
            instance_key=akiyo_match.group("instance_key"),
        )
    matched = _CHAT_KEY_RE.match(text)
    if matched:
        return ParsedChatKey(
            adapter_key=matched.group("adapter"),
            kind=matched.group("kind"),
            chat_id=matched.group("chat_id"),
        )
    if text.startswith("group_"):
        return ParsedChatKey("onebot_v11", "group", text.removeprefix("group_"))
    if text.startswith("private_"):
        return ParsedChatKey("onebot_v11", "private", text.removeprefix("private_"))
    return ParsedChatKey("onebot_v11", "group", text)


def extract_group_id(chat_key: str) -> str:
    parsed = parse_chat_key(chat_key)
    if not parsed.is_group:
        raise ValueError("群分析只能在群聊中使用")
    return parsed.chat_id
