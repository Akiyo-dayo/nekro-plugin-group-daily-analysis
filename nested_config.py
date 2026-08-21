from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

_SCHEMA_DEFAULTS_PATH = Path(__file__).resolve().parent / "schema_defaults.json"


def load_schema_defaults() -> dict[str, Any]:
    return json.loads(_SCHEMA_DEFAULTS_PATH.read_text(encoding="utf-8"))


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        elif value is not None:
            merged[key] = copy.deepcopy(value)
    return merged


def parse_id_list(text: str) -> list[str]:
    if not text:
        return []
    items: list[str] = []
    for raw in text.replace("，", ",").replace(";", "\n").splitlines():
        for part in raw.split(","):
            value = part.strip()
            if value:
                items.append(value)
    return items


def parse_time_list(text: str) -> list[str]:
    items = parse_id_list(text)
    return items or ["23:00"]


class NestedConfig(dict):
    """供原 ConfigManager 使用的可变嵌套配置。"""

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        *,
        persist_path: Path | None = None,
        on_save: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        super().__init__(copy.deepcopy(data or {}))
        self._persist_path = persist_path
        self._on_save = on_save

    def replace_from(self, data: dict[str, Any]) -> None:
        """用新的嵌套配置整体替换内存中的值，不立刻落盘。"""
        self.clear()
        self.update(copy.deepcopy(data or {}))

    def save_config(self) -> None:
        payload = dict(self)
        if self._persist_path is not None:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if self._on_save is not None:
            self._on_save(payload)
