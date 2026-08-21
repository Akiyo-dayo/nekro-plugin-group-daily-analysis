from __future__ import annotations

from typing import Any

from pydantic import Field, create_model

from na_schema import extra_na_specs, iter_field_specs
from t2i_defaults import DEFAULT_T2I_API_PATH, DEFAULT_T2I_API_URL

from nekro_agent.api.plugin import ConfigBase, NekroPlugin

try:
    from nekro_agent.api.plugin import ExtraField
except ImportError:  # 原版 NA 可能只在 core_utils 导出
    from nekro_agent.core.core_utils import ExtraField

try:
    from nekro_agent.api import i18n

    def _i18n(text: str) -> Any:
        return i18n.i18n_text(zh_CN=text, en_US=text)
except Exception:  # pragma: no cover
    def _i18n(text: str) -> dict[str, str]:
        return {"zh-CN": text, "en-US": text}

plugin = NekroPlugin(
    name="群分析总结插件",
    module_name="group_daily_analysis",
    description=(
        "群日常分析总结插件：话题、称号、金句、活跃度报告与群漫画。"
        "移植自 SXP-Simon/astrbot_plugin_qq_group_daily_analysis。"
    ),
    version="5.1.2",
    author="SXPSimon",
    url="https://github.com/Akiyo-dayo/nekro-plugin-group-daily-analysis",
    support_adapter=["onebot_v11", "discord", "telegram", "qqbot_openclaw"],
    allow_sleep=False,
    sleep_brief="定时群分析与增量统计需要持续运行，因此禁止休眠。",
)


def _json_extra(spec: Any) -> dict[str, Any]:
    extra: dict[str, Any] = {
        "i18n_category": _i18n(spec.category),
        "i18n_title": _i18n(spec.title),
        "i18n_description": _i18n(spec.description),
    }
    if spec.is_textarea:
        extra["is_textarea"] = True
    if spec.is_hidden:
        extra["is_hidden"] = True
    if spec.ref_model_groups:
        extra["ref_model_groups"] = True
        extra["model_type"] = spec.model_type or "chat"
    if spec.ref_presets:
        extra["ref_presets"] = True
    if spec.is_list:
        extra["sub_item_name"] = spec.sub_item_name
    try:
        return ExtraField(**{k: v for k, v in extra.items() if k.startswith("i18n_") or k in {
            "is_textarea", "is_hidden", "ref_model_groups", "model_type", "ref_presets", "sub_item_name"
        }}).model_dump(exclude_none=True)
    except Exception:
        return extra


def _field_kwargs(spec: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "title": spec.title,
        "description": spec.description,
        "json_schema_extra": _json_extra(spec),
    }
    if spec.is_list:
        kwargs["default_factory"] = lambda value=list(spec.default or []): list(value)
    else:
        kwargs["default"] = spec.default
    return kwargs


def _build_plugin_config() -> type[ConfigBase]:
    fields: dict[str, tuple[Any, Any]] = {}
    for spec in iter_field_specs() + extra_na_specs():
        fields[spec.na_name] = (spec.python_type, Field(**_field_kwargs(spec)))
    return create_model(
        "PluginConfig",
        __base__=ConfigBase,
        __doc__="群分析插件配置，字段与原版 AstrBot `_conf_schema.json` 对齐。",
        **fields,
    )


PluginConfig = plugin.mount_config()(_build_plugin_config())
config: PluginConfig = plugin.get_config(PluginConfig)
_ = (DEFAULT_T2I_API_URL, DEFAULT_T2I_API_PATH)
