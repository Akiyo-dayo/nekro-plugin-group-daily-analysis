"""NekroAgent 群日常分析插件。

移植自 https://github.com/SXP-Simon/astrbot_plugin_qq_group_daily_analysis
"""

from __future__ import annotations

import sys
from pathlib import Path

_PLUGIN_DIR = Path(__file__).resolve().parent
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))


def _ensure_runtime_deps() -> None:
    """原版 NA 镜像不含移植内核依赖；akiyo 版通常已预装，导入成功则跳过。"""
    try:
        from nekro_agent.core.os_env import PLUGIN_DYNAMIC_PACKAGE_DIR

        dyn = Path(PLUGIN_DYNAMIC_PACKAGE_DIR)
        dyn.mkdir(parents=True, exist_ok=True)
        if str(dyn) not in sys.path:
            sys.path.insert(0, str(dyn))
    except Exception:
        pass

    from nekro_agent.api.plugin import dynamic_import_pkg

    for spec, import_name in (
        ("httpx", "httpx"),
        ("aiohttp", "aiohttp"),
        ("diskcache", "diskcache"),
        ("ulid-py", "ulid"),
        ("markupsafe", "markupsafe"),
        ("pillow", "PIL"),
        ("jinja2", "jinja2"),
    ):
        try:
            __import__(import_name)
        except ImportError:
            dynamic_import_pkg(
                spec,
                import_name,
                mirror="https://mirrors.aliyun.com/pypi/simple",
            )


_ensure_runtime_deps()

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
