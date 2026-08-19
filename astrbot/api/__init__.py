from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any, Mapping

logger = logging.getLogger("nekro.plugin.group_daily_analysis")

AstrBotConfig = dict


async def _sp_get_async(*_args: Any, default: Any = None, **_kwargs: Any) -> Any:
    return {} if default is None else default


sp = SimpleNamespace(get_async=_sp_get_async)

__all__ = ["AstrBotConfig", "logger", "sp"]
