from __future__ import annotations

# 国内加速节点。AstrBot 官方端点 t2i.soulter.top 对长报告经常 502/超时。
DEFAULT_T2I_API_URL = "https://t2i.vercel.ciallo.de5.net"
DEFAULT_T2I_API_PATH = "/generate"
LEGACY_OFFICIAL_T2I_API_URL = "https://t2i.soulter.top/text2img"


def resolve_t2i_endpoint(
    api_url: str | None, api_path: str | None = None
) -> tuple[str, str]:
    url = (api_url or "").strip().rstrip("/")
    if not url or url == LEGACY_OFFICIAL_T2I_API_URL.rstrip("/"):
        url = DEFAULT_T2I_API_URL
    path = (api_path or "").strip() or DEFAULT_T2I_API_PATH
    return url.rstrip("/"), path
