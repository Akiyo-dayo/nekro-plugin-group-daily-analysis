from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class HistoryRecord:
    id: int
    content: dict[str, Any]
    sender_id: str
    sender_name: str
    created_at: datetime


class LocalMessageHistoryManager:
    """给 QQ 官方 / Telegram 用的本地消息缓存，兼容原 message_history_manager 接口。"""

    def __init__(self, root: Path, max_messages: int = 10000) -> None:
        self.root = root
        self.max_messages = max_messages
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, platform_id: str, user_id: str) -> Path:
        safe_platform = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in platform_id)
        safe_user = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in user_id)
        return self.root / f"{safe_platform}__{safe_user}.json"

    def _load(self, platform_id: str, user_id: str) -> list[dict[str, Any]]:
        path = self._path(platform_id, user_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return data if isinstance(data, list) else []

    def _dump(self, platform_id: str, user_id: str, rows: list[dict[str, Any]]) -> None:
        path = self._path(platform_id, user_id)
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    async def insert(
        self,
        platform_id: str,
        user_id: str,
        content: dict[str, Any],
        sender_id: str,
        sender_name: str,
        max_messages: int | None = None,
        **_kwargs: Any,
    ) -> None:
        rows = self._load(platform_id, user_id)
        next_id = int(rows[-1]["id"]) + 1 if rows else 1
        rows.append(
            {
                "id": next_id,
                "content": content,
                "sender_id": str(sender_id),
                "sender_name": str(sender_name),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        limit = max_messages or self.max_messages
        if limit and len(rows) > limit:
            rows = rows[-limit:]
        self._dump(platform_id, user_id, rows)

    async def get(
        self,
        platform_id: str,
        user_id: str,
        page: int = 1,
        page_size: int = 100,
        **_kwargs: Any,
    ) -> list[HistoryRecord]:
        rows = self._load(platform_id, user_id)
        newest_first = list(reversed(rows))
        start = max(page - 1, 0) * max(page_size, 1)
        end = start + max(page_size, 1)
        slice_rows = newest_first[start:end]
        records: list[HistoryRecord] = []
        for row in slice_rows:
            created_raw = str(row.get("created_at") or "")
            try:
                created_at = datetime.fromisoformat(created_raw)
            except ValueError:
                created_at = datetime.now(timezone.utc)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            records.append(
                HistoryRecord(
                    id=int(row.get("id") or 0),
                    content=row.get("content") or {},
                    sender_id=str(row.get("sender_id") or ""),
                    sender_name=str(row.get("sender_name") or ""),
                    created_at=created_at,
                )
            )
        return records
