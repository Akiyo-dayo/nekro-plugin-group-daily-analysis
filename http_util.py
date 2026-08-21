from __future__ import annotations

import json
from typing import Any

import httpx


def chat_completions_url(base_url: str) -> str:
    """把模型组 BASE_URL 规范成 OpenAI 兼容的 chat/completions 地址。"""
    url = (base_url or "").strip().rstrip("/")
    if not url:
        raise RuntimeError("模型组 BASE_URL 为空")
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return f"{url}/chat/completions"
    if url.endswith("/v1/"):
        return f"{url}chat/completions"
    return f"{url}/v1/chat/completions"


def httpx_client_kwargs(*, timeout: Any = 60.0, proxy: str | None = None) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"timeout": timeout}
    if proxy:
        kwargs["proxy"] = proxy
    return kwargs


async def post_json(url: str, payload: dict[str, Any], *, headers: dict[str, str] | None = None, timeout: float = 120.0, proxy: str | None = None) -> httpx.Response:
    kwargs = httpx_client_kwargs(timeout=httpx.Timeout(timeout), proxy=proxy)
    try:
        async with httpx.AsyncClient(**kwargs) as client:
            return await client.post(url, json=payload, headers=headers)
    except TypeError:
        kwargs.pop("proxy", None)
        if proxy:
            kwargs["proxies"] = proxy
        async with httpx.AsyncClient(**kwargs) as client:
            return await client.post(url, json=payload, headers=headers)
