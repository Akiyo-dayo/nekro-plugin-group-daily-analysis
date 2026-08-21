from __future__ import annotations

from typing import Any


def draw_provider_from_group(group: Any, name: str, mode: str) -> dict[str, Any] | None:
    """把 NA 模型组转成内置 DrawingClient 能用的供应商条目。不含密钥的组会被跳过。"""
    if group is None:
        return None
    api_key = str(getattr(group, "API_KEY", "") or "").strip()
    if not api_key:
        return None
    protocol = "images" if str(mode or "").strip() in {"图像生成", "images", "image"} else "chat"
    return {
        "enable": True,
        "name": name or "na-draw",
        "api_url": str(getattr(group, "BASE_URL", "") or "").strip(),
        "api_key": api_key,
        "model": str(getattr(group, "CHAT_MODEL", "") or "").strip(),
        "proxy": str(getattr(group, "CHAT_PROXY", "") or "").strip(),
        "api_protocol": protocol,
        "timeout": 600,
        "image_size": "2K",
        "aspect_ratio": "16:9",
        "_priority": 1000,
        "_index": -1,
    }


def iter_draw_model_groups() -> dict[str, Any]:
    try:
        from nekro_agent.api import core
    except Exception:
        return {}
    groups = getattr(core.config, "MODEL_GROUPS", {}) or {}
    result = {}
    for group_name, group in groups.items():
        if str(getattr(group, "MODEL_TYPE", "") or "") == "draw":
            result[group_name] = group
    return result


def pick_draw_model_group(
    name: str, draw_groups: dict[str, Any], all_groups: dict[str, Any]
) -> Any | None:
    """按名字解析绘图模型组。点了具体名字却找不到时不悄悄换组。"""
    key = str(name or "").strip()
    if key:
        if key in draw_groups:
            return draw_groups[key]
        if key in all_groups:
            return all_groups[key]
        return None
    for fallback in ("default-draw", "default-draw-chat"):
        if fallback in draw_groups:
            return draw_groups[fallback]
        if fallback in all_groups:
            return all_groups[fallback]
    if draw_groups:
        return next(iter(draw_groups.values()))
    return None


def get_draw_model_group(name: str) -> Any | None:
    """解析漫画出图用的 NA 模型组。优先 draw 类型，也允许点名已有组。"""
    try:
        from nekro_agent.api import core
    except Exception:
        return None
    draw_groups = iter_draw_model_groups()
    all_groups = getattr(core.config, "MODEL_GROUPS", {}) or {}
    return pick_draw_model_group(name, draw_groups, all_groups)
