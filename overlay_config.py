from __future__ import annotations

import json
from typing import Any

from na_schema import assign_path, coerce_field_value, extra_na_specs, iter_field_specs
from nested_config import deep_merge


def overlay_na_config(defaults: dict[str, Any], cfg: Any) -> dict[str, Any]:
    """把 NA 扁平配置叠到原插件的分组嵌套配置上。"""
    overlay: dict[str, Any] = {}
    for spec in extra_na_specs() + iter_field_specs():
        if not spec.path or not hasattr(cfg, spec.na_name):
            continue
        raw = getattr(cfg, spec.na_name)
        if spec.is_textarea and not spec.is_json and spec.path[0] == "prompts":
            if not str(raw or "").strip():
                continue
        assign_path(overlay, spec.path, coerce_field_value(spec, raw))

    merged = deep_merge(defaults, overlay)
    extra_raw = str(getattr(cfg, "CORE_CONFIG_JSON", "") or "").strip()
    if extra_raw:
        extra = json.loads(extra_raw)
        if not isinstance(extra, dict):
            raise ValueError("CORE_CONFIG_JSON 必须是 JSON 对象")
        merged = deep_merge(merged, extra)
    return merged
