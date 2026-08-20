from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable

logger = logging.getLogger("nekro.plugin.group_daily_analysis.cron")


class CronTrigger:
    """最小 cron 触发器：每天在指定时分触发。不依赖 APScheduler。"""

    def __init__(self, hour: int, minute: int) -> None:
        self.hour = int(hour)
        self.minute = int(minute)

    def next_fire(self, now: datetime | None = None) -> datetime:
        now = now or datetime.now()
        candidate = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate


class _Job:
    def __init__(
        self,
        job_id: str,
        func: Callable[[], Any],
        trigger: CronTrigger,
        misfire_grace_time: int = 60,
    ) -> None:
        self.id = job_id
        self.func = func
        self.trigger = trigger
        self.misfire_grace_time = misfire_grace_time
        self._task: asyncio.Task | None = None


class AsyncIOScheduler:
    """足够支撑群分析定时报告的 asyncio 调度器，兼容 APScheduler 的常用调用。"""

    def __init__(self) -> None:
        self.running = False
        self._jobs: dict[str, _Job] = {}

    def add_job(
        self,
        func: Callable[[], Any],
        trigger: CronTrigger,
        id: str,
        replace_existing: bool = False,
        misfire_grace_time: int = 60,
        **_kwargs: Any,
    ) -> _Job:
        if id in self._jobs:
            if not replace_existing:
                raise ValueError(f"job {id} already exists")
            self.remove_job(id)
        job = _Job(id, func, trigger, misfire_grace_time)
        self._jobs[id] = job
        if self.running:
            job._task = asyncio.create_task(self._run_job(job), name=f"gda-cron-{id}")
        return job

    def get_job(self, job_id: str) -> _Job | None:
        return self._jobs.get(job_id)

    def remove_job(self, job_id: str) -> None:
        job = self._jobs.pop(job_id, None)
        if job and job._task and not job._task.done():
            job._task.cancel()

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        for job in self._jobs.values():
            job._task = asyncio.create_task(self._run_job(job), name=f"gda-cron-{job.id}")

    def shutdown(self, wait: bool = False) -> None:
        self.running = False
        tasks = [job._task for job in self._jobs.values() if job._task and not job._task.done()]
        for task in tasks:
            task.cancel()
        self._jobs.clear()
        if wait and tasks:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(asyncio.gather(*tasks, return_exceptions=True))

    async def _run_job(self, job: _Job) -> None:
        while self.running and job.id in self._jobs:
            delay = (job.trigger.next_fire() - datetime.now()).total_seconds()
            if delay > 0:
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    return
            if not self.running or job.id not in self._jobs:
                return
            try:
                result = job.func()
                if asyncio.iscoroutine(result):
                    await result
            except asyncio.CancelledError:
                return
            except Exception:
                logger.exception("定时任务执行失败: %s", job.id)


class CronManager:
    """兼容原插件 context.cron_manager.scheduler 的调度包装。"""

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    async def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
