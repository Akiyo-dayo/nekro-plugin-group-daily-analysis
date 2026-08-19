from __future__ import annotations

# 与 AstrBot 框架默认出图端点一致，留空时走这里。
DEFAULT_T2I_API_URL = "https://t2i.soulter.top/text2img"
DEFAULT_T2I_API_PATH = "/generate"


def resolve_t2i_endpoint(
    api_url: str | None, api_path: str | None = None
) -> tuple[str, str]:
    url = (api_url or "").strip() or DEFAULT_T2I_API_URL
    path = (api_path or "").strip() or DEFAULT_T2I_API_PATH
    return url.rstrip("/"), path
