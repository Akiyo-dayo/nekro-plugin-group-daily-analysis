from __future__ import annotations

import base64
import logging
from typing import Any
from urllib.parse import urljoin

from http_util import post_json
from t2i_defaults import resolve_t2i_endpoint
from nekro_agent.api import core

logger = logging.getLogger("group_daily_analysis")


class HtmlRenderService:
    """兼容 AstrBot Star.html_render 签名的 T2I 客户端。"""

    def __init__(self, api_url: str = "", api_path: str = "") -> None:
        self.api_url, self.api_path = resolve_t2i_endpoint(api_url, api_path)

    def configure(self, api_url: str = "", api_path: str = "") -> None:
        self.api_url, self.api_path = resolve_t2i_endpoint(api_url, api_path)

    async def __call__(
        self,
        tmpl: str,
        data: dict[str, Any] | None = None,
        return_url: bool = False,
        options: dict[str, Any] | None = None,
    ) -> bytes | str | None:
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
        timeout_s = max(timeout_ms / 1000, 30.0)
        response = await post_json(
            url,
            payload,
            timeout=timeout_s,
            proxy=proxy or None,
        )
        if response.status_code >= 500:
            logger.warning(
                f"T2I 返回 {response.status_code}，去掉高级出图参数后重试一次"
            )
            response = await post_json(
                url,
                {
                    "tmpl": tmpl,
                    "html": tmpl,
                    "data": data or {},
                    "return_url": return_url,
                },
                timeout=max(timeout_s, 60.0),
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
