from __future__ import annotations

import json
from typing import Any

import httpx


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
