from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, AsyncIterator

from http_util import chat_completions_url, post_json
from astrbot.api.provider import LLMResponse
from nekro_agent.api import core


@dataclass
class _Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    input: int = 0
    output: int = 0
    total: int = 0


class NAProvider:
    def __init__(self, group_name: str, model_group: Any) -> None:
        self.group_name = group_name
        self.model_group = model_group
        extra_body = getattr(model_group, "EXTRA_BODY", None)
        if isinstance(extra_body, str) and extra_body.strip():
            try:
                extra_body = json.loads(extra_body)
            except json.JSONDecodeError:
                extra_body = None
        self.provider_config = {
            "temperature": getattr(model_group, "TEMPERATURE", None),
            "custom_extra_body": extra_body if isinstance(extra_body, dict) else {},
        }

    def meta(self) -> SimpleNamespace:
        return SimpleNamespace(id=self.group_name)

    async def text_chat_stream(self, **kwargs: Any) -> AsyncIterator[LLMResponse]:
        response = await self.generate(**kwargs)
        yield response

    async def generate(self, **kwargs: Any) -> LLMResponse:
        prompt = str(kwargs.get("prompt") or "")
        system_prompt = kwargs.get("system_prompt")
        response_format = kwargs.get("response_format")
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": str(system_prompt)})
        messages.append({"role": "user", "content": prompt})

        model = str(getattr(self.model_group, "CHAT_MODEL", "") or "").strip()
        if not model:
            raise RuntimeError(f"模型组 {self.group_name} 未配置 CHAT_MODEL")

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if self.model_group.TEMPERATURE is not None:
            payload["temperature"] = self.model_group.TEMPERATURE
        if getattr(self.model_group, "TOP_P", None) is not None:
            payload["top_p"] = self.model_group.TOP_P
        extra_body = self.provider_config.get("custom_extra_body") or {}
        if extra_body:
            payload.update(extra_body)
        if response_format:
            payload["response_format"] = response_format

        headers = {"Authorization": f"Bearer {self.model_group.API_KEY}"}
        proxy = self.model_group.CHAT_PROXY or getattr(core.config, "DEFAULT_PROXY", None) or None
        url = chat_completions_url(str(self.model_group.BASE_URL or ""))
        response = await post_json(
            url,
            payload,
            headers=headers,
            timeout=120.0,
            proxy=proxy,
        )
        if response.status_code >= 400:
            body = (response.text or "").strip().replace("\n", " ")[:500]
            raise RuntimeError(
                f"LLM HTTP {response.status_code} provider={self.group_name}: {body or 'empty body'}"
            )
        data = response.json()
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(f"LLM error provider={self.group_name}: {data.get('error')}")

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        text = message.get("content") or message.get("reasoning_content") or ""
        if isinstance(text, list):
            text = "".join(
                str(part.get("text") or part) if isinstance(part, dict) else str(part)
                for part in text
            )
        if not str(text).strip():
            raise RuntimeError(f"LLM 返回空内容 provider={self.group_name}")
        usage_raw = data.get("usage") or {}
        prompt_tokens = int(usage_raw.get("prompt_tokens") or 0)
        completion_tokens = int(usage_raw.get("completion_tokens") or 0)
        total_tokens = int(usage_raw.get("total_tokens") or (prompt_tokens + completion_tokens))
        usage = _Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            input=prompt_tokens,
            output=completion_tokens,
            total=total_tokens,
        )
        return LLMResponse(
            role="assistant",
            completion_text=text,
            usage=usage,
            raw_completion=SimpleNamespace(usage=usage),
        )


def iter_chat_model_groups() -> dict[str, Any]:
    groups = getattr(core.config, "MODEL_GROUPS", {}) or {}
    result = {}
    for name, group in groups.items():
        model_type = getattr(group, "MODEL_TYPE", "chat")
        if model_type in ("chat", None, ""):
            result[name] = group
    return result


def get_model_group(name: str) -> Any:
    groups = iter_chat_model_groups()
    if name and name in groups:
        return groups[name]
    if "default" in groups:
        return groups["default"]
    if groups:
        return next(iter(groups.values()))
    raise RuntimeError("NA 未配置任何 chat 模型组")


class NAPersona:
    def __init__(self, system_prompt: str) -> None:
        self.system_prompt = system_prompt
        self.prompt = system_prompt


class NAPersonaManager:
    """把 NA 人设接到原插件 persona_manager 接口。"""

    async def get_persona(self, persona_id: Any) -> NAPersona | None:
        prompt = await self._load_prompt(persona_id)
        if not prompt:
            return None
        return NAPersona(prompt)

    async def get_default_persona_v3(self, _umo: str | None = None) -> dict[str, str]:
        prompt = str(getattr(core.config, "AI_CHAT_PRESET_SETTING", "") or "").strip()
        default_id = getattr(core.config, "AI_CHAT_DEFAULT_PRESET_ID", None)
        if default_id not in (None, ""):
            loaded = await self._load_prompt(default_id)
            if loaded:
                prompt = loaded
        return {"prompt": prompt}

    async def _load_prompt(self, persona_id: Any) -> str:
        if persona_id in (None, "", "[%None]"):
            return ""
        try:
            from nekro_agent.models.db_preset import DBPreset

            if str(persona_id).isdigit():
                preset = await DBPreset.get_or_none(id=int(persona_id))
                if preset is not None:
                    return str(getattr(preset, "content", "") or "").strip()
            presets = await DBPreset.all()
            for preset in presets:
                name = str(getattr(preset, "name", "") or "")
                if name == str(persona_id):
                    return str(getattr(preset, "content", "") or "").strip()
        except Exception:
            pass
        if str(persona_id) in {
            str(getattr(core.config, "AI_CHAT_PRESET_NAME", "") or ""),
            "default",
        }:
            return str(getattr(core.config, "AI_CHAT_PRESET_SETTING", "") or "").strip()
        return ""


class NAContext:
    def __init__(self, default_group: str, cron_manager: Any) -> None:
        self.default_group = default_group or "default"
        self.cron_manager = cron_manager
        self.conversation_manager = None
        self.persona_manager = NAPersonaManager()
        self.message_history_manager = None
        self.platform_manager = None
        self._providers = {
            name: NAProvider(name, group) for name, group in iter_chat_model_groups().items()
        }
        if self.default_group not in self._providers:
            try:
                group = get_model_group(self.default_group)
                self._providers[self.default_group] = NAProvider(self.default_group, group)
            except Exception:
                pass

    def get_provider_by_id(self, provider_id: str | None = None, **_kwargs: Any) -> NAProvider | None:
        if not provider_id:
            return self._providers.get(self.default_group)
        return self._providers.get(provider_id)

    def get_all_providers(self) -> list[NAProvider]:
        return list(self._providers.values())

    async def get_current_chat_provider_id(self, umo: str | None = None) -> str | None:
        if self.default_group in self._providers:
            return self.default_group
        if self._providers:
            return next(iter(self._providers))
        return None

    async def llm_generate(self, **kwargs: Any) -> LLMResponse:
        provider_id = kwargs.get("chat_provider_id") or self.default_group
        provider = self.get_provider_by_id(str(provider_id))
        if provider is None:
            raise RuntimeError(f"模型组不存在: {provider_id}")
        return await provider.generate(**kwargs)

    def refresh_providers(self, default_group: str) -> None:
        self.default_group = default_group or self.default_group
        self._providers = {
            name: NAProvider(name, group) for name, group in iter_chat_model_groups().items()
        }
        if self.default_group not in self._providers:
            try:
                group = get_model_group(self.default_group)
                self._providers[self.default_group] = NAProvider(self.default_group, group)
            except Exception:
                pass
