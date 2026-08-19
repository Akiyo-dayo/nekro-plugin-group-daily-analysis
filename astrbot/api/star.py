from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

_data_dir_factory: Callable[[str], Path] | None = None


def set_data_dir_factory(factory: Callable[[str], Path]) -> None:
    global _data_dir_factory
    _data_dir_factory = factory


class StarTools:
    @staticmethod
    def get_data_dir(_plugin_name: str = "") -> Path:
        if _data_dir_factory is None:
            return Path.cwd() / "data" / "group_daily_analysis"
        return _data_dir_factory(_plugin_name)


class Star:
    """占位基类，供类型标注使用。"""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass


class Context:
    """由 NA 运行时注入的兼容上下文。"""

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)
