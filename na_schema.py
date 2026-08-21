"""把原版 AstrBot `_conf_schema.json` 展平为 NA WebUI 字段。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator

_SCHEMA_PATH = Path(__file__).resolve().parent / "_conf_schema.json"
_JSON_TYPES = {"template_list", "file"}
_NAME_ALIASES = {
    "llm_provider_id": "MODEL_GROUP",
}


@dataclass(frozen=True)
class FieldSpec:
    na_name: str
    path: tuple[str, ...]
    title: str
    description: str
    category: str
    default: Any
    python_type: Any
    options: tuple[str, ...] = ()
    is_list: bool = False
    is_textarea: bool = False
    is_hidden: bool = False
    is_json: bool = False
    ref_model_groups: bool = False
    model_type: str = "chat"
    ref_presets: bool = False
    sub_item_name: str = "项目"


def load_conf_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    from nested_config import parse_id_list

    return parse_id_list(str(value))


def _as_time_list(value: Any) -> list[str]:
    items = _as_str_list(value)
    return items or ["23:00"]


StrList = Annotated[list[str], BeforeValidator(_as_str_list)]
TimeList = Annotated[list[str], BeforeValidator(_as_time_list)]


def _literal(options: list[str]) -> Any:
    return Literal.__getitem__(tuple(options))


def _na_name(key: str) -> str:
    return _NAME_ALIASES.get(key, key.upper())


def _normalize_default(spec: dict[str, Any], is_json: bool) -> Any:
    default = spec.get("default")
    if is_json:
        if isinstance(default, str):
            return default
        return json.dumps(default if default is not None else [], ensure_ascii=False, indent=2)
    if default is None:
        kind = spec.get("type")
        if kind == "list":
            return []
        if kind == "bool":
            return False
        if kind in {"int", "float"}:
            return 0
        return ""
    return default


def _walk_items(
    items: dict[str, Any],
    category: str,
    path: tuple[str, ...],
    specs: list[FieldSpec],
) -> None:
    for key, spec in items.items():
        if not isinstance(spec, dict):
            continue
        kind = str(spec.get("type") or "")
        nested = spec.get("items")
        if kind == "object" and isinstance(nested, dict):
            child_category = str(spec.get("description") or category)
            _walk_items(nested, child_category, path + (key,), specs)
            continue
        options = tuple(str(item) for item in (spec.get("options") or []) if str(item))
        is_json = kind in _JSON_TYPES
        is_list = kind == "list" and not is_json
        is_textarea = kind == "text" or bool(spec.get("editor_mode")) or is_json
        title = str(spec.get("description") or key)
        hint = str(spec.get("hint") or title)
        default = _normalize_default(spec, is_json)
        python_type: Any = str
        if kind == "bool":
            python_type = bool
        elif kind == "int":
            python_type = int
        elif kind == "float":
            python_type = float
        elif is_list:
            if key == "auto_analysis_time":
                python_type = TimeList
            elif options:
                python_type = Annotated[
                    list[_literal(list(options))],
                    BeforeValidator(_as_str_list),
                ]
            else:
                python_type = StrList
            if not isinstance(default, list):
                default = []
        elif kind in {"string", "text"} and options and str(default) in options:
            python_type = _literal(list(options))
        elif is_json:
            python_type = str
        na_name = _na_name(key)
        if na_name == "MODEL_GROUP" and not default:
            default = "default"
        ref_model = key.endswith("provider_id")
        ref_presets = spec.get("_special") == "select_persona" or key.endswith("persona_id")
        specs.append(
            FieldSpec(
                na_name=na_name,
                path=path + (key,),
                title=title,
                description=hint,
                category=category,
                default=default,
                python_type=python_type,
                options=options,
                is_list=is_list,
                is_textarea=is_textarea,
                is_hidden=bool(spec.get("invisible")),
                is_json=is_json,
                ref_model_groups=ref_model,
                ref_presets=ref_presets,
                sub_item_name=title,
            )
        )


def iter_field_specs() -> list[FieldSpec]:
    schema = load_conf_schema()
    specs: list[FieldSpec] = []
    used: set[str] = set()
    for group_key, group in schema.items():
        if not isinstance(group, dict):
            continue
        category = str(group.get("description") or group_key)
        items = group.get("items")
        if not isinstance(items, dict):
            continue
        before = len(specs)
        _walk_items(items, category, (group_key,), specs)
        for spec in specs[before:]:
            if spec.na_name in used:
                raise ValueError(f"配置字段名冲突: {spec.na_name}")
            used.add(spec.na_name)
    return specs


def extra_na_specs() -> list[FieldSpec]:
    from t2i_defaults import DEFAULT_T2I_API_PATH, DEFAULT_T2I_API_URL

    return [
        FieldSpec(
            na_name="EXPOSE_AGENT_TOOLS",
            path=(),
            title="向 Agent 暴露工具",
            description="关闭后，沙盒内不再出现群分析 / 群漫画等 Agent 工具，命令与定时任务仍可用。",
            category="NekroAgent 适配",
            default=True,
            python_type=bool,
        ),
        FieldSpec(
            na_name="T2I_API_URL",
            path=(),
            title="T2I 渲染服务地址",
            description=(
                "图片报告出图服务。默认使用国内加速节点 https://t2i.vercel.ciallo.de5.net 。"
                "原先保存的官方地址 t2i.soulter.top 会自动切到国内节点，避免长报告 502 后只发文字。"
                "自建可填本机地址；留空同样回落到国内加速。"
            ),
            category="NekroAgent 适配",
            default=DEFAULT_T2I_API_URL,
            python_type=str,
        ),
        FieldSpec(
            na_name="T2I_API_PATH",
            path=(),
            title="T2I 接口路径",
            description="一般不用改。官方与常见 HF 空间均为 /generate。",
            category="NekroAgent 适配",
            default=DEFAULT_T2I_API_PATH,
            python_type=str,
        ),
        FieldSpec(
            na_name="CORE_CONFIG_JSON",
            path=(),
            title="高级嵌套配置 JSON（覆盖用）",
            description=(
                "仅在需要临时覆盖原版嵌套结构时填写 JSON 对象。"
                "日常请用上方分组选项；留空则只用面板字段。"
            ),
            category="NekroAgent 适配",
            default="",
            python_type=str,
            is_textarea=True,
        ),
        FieldSpec(
            na_name="DRAW_MODEL_GROUP",
            path=("daily_comic", "draw_model_group"),
            title="漫画绘图模型组",
            description=(
                "从 NA「系统配置 → 模型组」里选择类型为绘图(draw) 的组，Key 和接口地址都在模型组里配。"
                "不要和上面的「画图提示词模型」搞混：那个只生成分镜文案。"
                "默认 default-draw。若要用 gpt-image-2 等，请把对应模型组的类型改成绘图。"
            ),
            category="每日群漫画",
            default="default-draw",
            python_type=str,
            ref_model_groups=True,
            model_type="draw",
        ),
        FieldSpec(
            na_name="DRAW_MODEL_MODE",
            path=("daily_comic", "draw_model_mode"),
            title="漫画绘图调用格式",
            description=(
                "聊天模式：走 chat/completions，适合 Gemini / Banana 等对话式生图。"
                "图像生成：走 images/generations，适合 Kolors、DALL·E、GPT-Image 官方接口。"
            ),
            category="每日群漫画",
            default="聊天模式",
            python_type=_literal(["聊天模式", "图像生成"]),
            options=("聊天模式", "图像生成"),
        ),
    ]


def coerce_field_value(spec: FieldSpec, raw: Any) -> Any:
    if spec.is_json:
        if isinstance(raw, (dict, list)):
            return raw
        text = str(raw or "").strip()
        if not text:
            return spec.default if not isinstance(spec.default, str) else json.loads(spec.default or "[]")
        parsed = json.loads(text)
        return parsed
    if spec.is_list:
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        from nested_config import parse_id_list, parse_time_list

        text = "" if raw is None else str(raw)
        if spec.na_name == "AUTO_ANALYSIS_TIME":
            return parse_time_list(text)
        return parse_id_list(text)
    if spec.python_type is bool:
        return bool(raw)
    if spec.python_type is int:
        return int(raw or 0)
    if spec.python_type is float:
        return float(raw or 0)
    if raw is None:
        return spec.default
    return raw


def assign_path(target: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    cursor = target
    for key in path[:-1]:
        child = cursor.get(key)
        if not isinstance(child, dict):
            child = {}
            cursor[key] = child
        cursor = child
    cursor[path[-1]] = value
