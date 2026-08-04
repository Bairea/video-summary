"""带指数退避与抖动的异步重试。取消通过 asyncio.Event 信号传递。"""

import asyncio
import random

from ..services.job_queue import JobCancelled


async def retry(fn, retries: int = 3, base_delay_ms: int = 200, max_delay_ms: int = 3000,
                jitter: float = 0.2, signal: asyncio.Event | None = None):
    attempt = 0
    while True:
        if signal is not None and signal.is_set():
            raise JobCancelled("aborted")
        try:
            return await fn(attempt)
        except JobCancelled:
            raise
        except Exception:
            if attempt >= retries:
                raise
            exp = min(max_delay_ms, base_delay_ms * (2 ** attempt))
            delay = max(0, round(exp + exp * jitter * (random.random() * 2 - 1)))
            await sleep(delay, signal)
            attempt += 1


async def sleep(ms: int, signal: asyncio.Event | None = None) -> None:
    if ms <= 0:
        return
    if signal is None:
        await asyncio.sleep(ms / 1000)
        return
    try:
        await asyncio.wait_for(signal.wait(), timeout=ms / 1000)
        raise JobCancelled("aborted")
    except asyncio.TimeoutError:
        return
