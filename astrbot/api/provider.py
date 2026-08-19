from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    role: str = "assistant"
    completion_text: str = ""
    usage: Any = None
    raw_completion: Any = None
    is_chunk: bool = False
    extra: dict[str, Any] = field(default_factory=dict)
