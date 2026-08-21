from __future__ import annotations

import json
from typing import Any

from na_schema import assign_path, coerce_field_value, extra_na_specs, iter_field_specs, read_path
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


def apply_nested_to_na_config(cfg: Any, payload: dict[str, Any]) -> None:
    """把命令写入的嵌套配置写回 NA WebUI 字段，避免下次刷新被面板旧值盖掉。"""
    if cfg is None or not isinstance(payload, dict):
        return
    for spec in extra_na_specs() + iter_field_specs():
        if not spec.path or not hasattr(cfg, spec.na_name):
            continue
        value = read_path(payload, spec.path)
        if value is None:
            continue
        if spec.is_json and not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, indent=2)
        setattr(cfg, spec.na_name, value)
    for name in ("dump_config", "save_config"):
        persist = getattr(cfg, name, None)
        if not callable(persist):
            continue
        try:
            persist()
            break
        except Exception:
            continue
