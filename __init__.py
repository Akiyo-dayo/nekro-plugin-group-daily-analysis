"""NekroAgent 群日常分析插件。

移植自 https://github.com/SXP-Simon/astrbot_plugin_qq_group_daily_analysis
"""

from __future__ import annotations

import sys
from pathlib import Path

_PLUGIN_DIR = Path(__file__).resolve().parent
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))

from plugin import PluginConfig, config, plugin  # noqa: E402,F401
from lifecycle import (  # noqa: E402,F401
    cleanup_plugin,
    init_plugin,
    on_plugin_disabled,
    on_plugin_enabled,
    on_user_message,
)
import commands as _commands  # noqa: E402,F401
import sandbox as _sandbox  # noqa: E402,F401

__all__ = ["plugin", "config", "PluginConfig"]
