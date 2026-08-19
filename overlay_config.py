from __future__ import annotations

import json
from typing import Any

from nested_config import deep_merge, parse_id_list, parse_time_list


def overlay_na_config(defaults: dict[str, Any], cfg: Any) -> dict[str, Any]:
    """把 NA 扁平配置叠到原插件的分组嵌套配置上。"""
    overlay: dict[str, Any] = {
        "basic": {
            "group_list_mode": str(getattr(cfg, "GROUP_LIST_MODE", "none") or "none"),
            "group_list": parse_id_list(getattr(cfg, "GROUP_LIST", "") or ""),
            "analysis_days": int(getattr(cfg, "ANALYSIS_DAYS", 1) or 1),
            "max_messages": int(getattr(cfg, "MAX_MESSAGES", 1000) or 1000),
            "min_messages_threshold": int(
                getattr(cfg, "MIN_MESSAGES_THRESHOLD", 200) or 200
            ),
            "filter_bot_messages": bool(getattr(cfg, "FILTER_BOT_MESSAGES", True)),
            "output_format": parse_id_list(getattr(cfg, "OUTPUT_FORMAT", "image") or "image")
            or ["image"],
            "report_template": str(getattr(cfg, "REPORT_TEMPLATE", "scrapbook") or "scrapbook"),
            "enable_analysis_reply": bool(getattr(cfg, "ENABLE_ANALYSIS_REPLY", False)),
            "show_report_caption": bool(getattr(cfg, "SHOW_REPORT_CAPTION", True)),
            "debug_mode": bool(getattr(cfg, "DEBUG_MODE", False)),
        },
        "auto_analysis": {
            "auto_analysis_time": parse_time_list(
                getattr(cfg, "AUTO_ANALYSIS_TIME", "23:00") or "23:00"
            ),
            "scheduled_group_list_mode": str(
                getattr(cfg, "SCHEDULED_GROUP_LIST_MODE", "whitelist") or "whitelist"
            ),
            "scheduled_group_list": parse_id_list(
                getattr(cfg, "SCHEDULED_GROUP_LIST", "") or ""
            ),
        },
        "llm": {
            "llm_provider_id": str(getattr(cfg, "MODEL_GROUP", "default") or "default"),
        },
        "incremental": {
            "incremental_group_list_mode": str(
                getattr(cfg, "INCREMENTAL_GROUP_LIST_MODE", "whitelist") or "whitelist"
            ),
            "incremental_group_list": parse_id_list(
                getattr(cfg, "INCREMENTAL_GROUP_LIST", "") or ""
            ),
            "incremental_min_messages": int(
                getattr(cfg, "INCREMENTAL_MIN_MESSAGES", 300) or 300
            ),
            "incremental_report_immediately": bool(
                getattr(cfg, "INCREMENTAL_REPORT_IMMEDIATELY", False)
            ),
        },
        "daily_comic": {
            "enable_daily_comic": bool(getattr(cfg, "ENABLE_DAILY_COMIC", False)),
            "enable_auto_daily_comic": bool(getattr(cfg, "ENABLE_AUTO_DAILY_COMIC", True)),
            "comic_group_list_mode": str(
                getattr(cfg, "COMIC_GROUP_LIST_MODE", "inherit") or "inherit"
            ),
            "comic_group_list": parse_id_list(getattr(cfg, "COMIC_GROUP_LIST", "") or ""),
        },
        "html": {
            "html_base_url": str(getattr(cfg, "HTML_BASE_URL", "") or ""),
            "html_only_url": bool(getattr(cfg, "HTML_ONLY_URL", False)),
        },
    }
    merged = deep_merge(defaults, overlay)
    extra_raw = str(getattr(cfg, "CORE_CONFIG_JSON", "") or "").strip()
    if extra_raw:
        extra = json.loads(extra_raw)
        if not isinstance(extra, dict):
            raise ValueError("CORE_CONFIG_JSON 必须是 JSON 对象")
        merged = deep_merge(merged, extra)
    return merged
