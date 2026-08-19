from __future__ import annotations

import base64
from typing import Any
from urllib.parse import urljoin

from http_util import post_json
from nekro_agent.api import core


class HtmlRenderService:
    """兼容 AstrBot Star.html_render 签名的 T2I 客户端。"""

    def __init__(self, api_url: str, api_path: str = "/generate") -> None:
        self.api_url = (api_url or "").rstrip("/")
        self.api_path = api_path or "/generate"

    def configure(self, api_url: str, api_path: str = "/generate") -> None:
        self.api_url = (api_url or "").rstrip("/")
        self.api_path = api_path or "/generate"

    async def __call__(
        self,
        tmpl: str,
        data: dict[str, Any] | None = None,
        return_url: bool = False,
        options: dict[str, Any] | None = None,
    ) -> bytes | str | None:
        if not self.api_url:
            raise RuntimeError("未配置 T2I_API_URL，无法把 HTML 报告渲染成图片")

        payload = {
            "tmpl": tmpl,
            "html": tmpl,
            "data": data or {},
            "return_url": return_url,
            "options": options or {},
        }
        if options:
            payload.update(options)

        url = self.api_url if self.api_url.endswith(self.api_path.lstrip("/")) else urljoin(
            self.api_url + "/", self.api_path.lstrip("/")
        )
        timeout_ms = int((options or {}).get("timeout") or 60000)
        proxy = getattr(core.config, "DEFAULT_PROXY", None)
        response = await post_json(
            url,
            payload,
            timeout=max(timeout_ms / 1000, 30.0),
            proxy=proxy or None,
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            body = response.json()
            if return_url:
                return body.get("url") or body.get("image_url")
            if body.get("image_base64"):
                return base64.b64decode(body["image_base64"])
            if body.get("url"):
                import httpx

                async with httpx.AsyncClient(timeout=60.0) as client:
                    image = await client.get(body["url"])
                    image.raise_for_status()
                    return image.content
            return None
        if return_url:
            return str(response.url)
        return response.content
