from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, AsyncIterator

from http_util import post_json
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

        payload: dict[str, Any] = {
            "model": self.model_group.CHAT_MODEL,
            "messages": messages,
        }
        if self.model_group.TEMPERATURE is not None:
            payload["temperature"] = self.model_group.TEMPERATURE
        if response_format:
            payload["response_format"] = response_format

        headers = {"Authorization": f"Bearer {self.model_group.API_KEY}"}
        base_url = str(self.model_group.BASE_URL).rstrip("/")
        proxy = self.model_group.CHAT_PROXY or getattr(core.config, "DEFAULT_PROXY", None) or None
        response = await post_json(
            f"{base_url}/chat/completions",
            payload,
            headers=headers,
            timeout=120.0,
            proxy=proxy,
        )
        response.raise_for_status()
        data = response.json()

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        text = message.get("content") or ""
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


class NAContext:
    def __init__(self, default_group: str, cron_manager: Any) -> None:
        self.default_group = default_group or "default"
        self.cron_manager = cron_manager
        self.conversation_manager = None
        self.persona_manager = None
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
