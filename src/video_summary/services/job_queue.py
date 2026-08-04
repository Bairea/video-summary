"""单任务串行执行队列（asyncio）。与旧 TS jobQueue.ts 行为一致：同一时刻只跑一个任务，可取消。"""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


class JobCancelled(Exception):
    """任务被取消（用户取消或队列取消）。"""


@dataclass
class QueuedJob:
    task_id: str
    runner: Callable[[asyncio.Event], Awaitable[None]]
    signal: asyncio.Event = field(default_factory=asyncio.Event)


class JobQueue:
    def __init__(self) -> None:
        self._queue: deque[QueuedJob] = deque()
        self._running: QueuedJob | None = None
        self._notify: asyncio.Event = asyncio.Event()
        self._worker: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        if loop is not None:
            self._loop = loop
        self._ensure_worker()

    def enqueue(self, task_id: str, runner: Callable[[asyncio.Event], Awaitable[None]]) -> None:
        self._queue.append(QueuedJob(task_id=task_id, runner=runner))
        self._notify.set()
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._ensure_worker)
        else:
            self._ensure_worker()

    def cancel(self, task_id: str) -> bool:
        if self._running is not None and self._running.task_id == task_id:
            self._running.signal.set()
            return True
        for idx, job in enumerate(self._queue):
            if job.task_id == task_id:
                job.signal.set()
                del self._queue[idx]
                return True
        return False

    async def stop(self) -> None:
        self.cancel_all()
        if self._worker is not None:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
            self._worker = None

    def cancel_all(self) -> None:
        if self._running is not None:
            self._running.signal.set()
        while self._queue:
            self._queue.popleft()

    def _ensure_worker(self) -> None:
        if self._worker is not None and not self._worker.done():
            return
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        self._worker = self._loop.create_task(self._worker_loop())

    async def _worker_loop(self) -> None:
        while True:
            while not self._queue:
                self._notify.clear()
                await self._notify.wait()
            job = self._queue.popleft()
            self._running = job
            try:
                await job.runner(job.signal)
            except JobCancelled:
                pass
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("task %s pipeline failed", job.task_id)
            finally:
                self._running = None
