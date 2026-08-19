from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler


class CronManager:
    """兼容原插件 context.cron_manager.scheduler 的 APScheduler 包装。"""

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    async def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
