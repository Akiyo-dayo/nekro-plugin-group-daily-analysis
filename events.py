from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from astrbot.api.event import AstrMessageEvent
from chat_key import parse_chat_key


def _segment_type(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value or "")


def _content_segments(message: Any) -> list[SimpleNamespace]:
    segs: list[SimpleNamespace] = []
    for item in getattr(message, "content_data", None) or []:
        kind = _segment_type(getattr(item, "type", ""))
        if kind in {"text"}:
            text = str(getattr(item, "text", "") or "")
            segs.append(SimpleNamespace(type="text", text=text, data={"text": text}))
        elif kind in {"image"}:
            url = str(
                getattr(item, "remote_url", None)
                or getattr(item, "local_path", None)
                or ""
            )
            segs.append(SimpleNamespace(type="image", url=url, file=url, data={"url": url}))
        elif kind in {"at"}:
            target = str(getattr(item, "target_platform_userid", "") or "")
            name = str(getattr(item, "target_nickname", "") or "")
            segs.append(
                SimpleNamespace(
                    type="at",
                    target=target,
                    qq=target,
                    name=name,
                    data={"qq": target, "target": target},
                )
            )
        elif kind in {"file", "voice", "video"}:
            url = str(
                getattr(item, "remote_url", None)
                or getattr(item, "local_path", None)
                or ""
            )
            name = str(getattr(item, "file_name", "") or "")
            segs.append(
                SimpleNamespace(
                    type=kind,
                    url=url,
                    file=url,
                    name=name,
                    data={"url": url, "name": name},
                )
            )
    if not segs:
        text = str(getattr(message, "content_text", "") or "")
        if text:
            segs.append(SimpleNamespace(type="text", text=text, data={"text": text}))
    return segs


def chat_message_to_event(
    message: Any,
    *,
    bot: Any = None,
    self_id: str = "",
) -> AstrMessageEvent:
    parsed = parse_chat_key(str(getattr(message, "chat_key", "") or ""))
    sender_name = str(
        getattr(message, "sender_nickname", "")
        or getattr(message, "sender_name", "")
        or getattr(message, "sender_id", "")
        or ""
    )
    message_id = str(getattr(message, "message_id", "") or "")
    segs = _content_segments(message)
    message_obj = SimpleNamespace(
        message=segs,
        message_id=message_id,
        sender=SimpleNamespace(nickname=sender_name, user_id=getattr(message, "sender_id", "")),
        raw_message={
            "group_openid": parsed.chat_id,
            "author": {
                "member_openid": str(getattr(message, "sender_id", "") or ""),
                "username": sender_name,
            },
        },
    )
    event = AstrMessageEvent(
        sender_id=str(getattr(message, "sender_id", "") or ""),
        sender_name=sender_name,
        group_id=parsed.chat_id if parsed.is_group else "",
        platform_id=parsed.adapter_key,
        platform_name=parsed.platform_name,
        message_str=str(getattr(message, "content_text", "") or ""),
        message_obj=message_obj,
        unified_msg_origin=parsed.umo,
        message_id=message_id,
    )
    event.bot = bot
    event._self_id = self_id
    return event
