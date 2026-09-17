"""AI 网关客户端共用小工具：Base URL 归一化与可取消等待。"""

import asyncio
import re


def normalize_base_url(input_url: str) -> str:
    """去掉首尾空白/末尾斜杠与重复的 /v1 后缀（协议路径由客户端自行拼接）。"""
    s = str(input_url or "").strip()
    if not s:
        return ""
    no_slash = s.rstrip("/")
    return re.sub(r"/v1$", "", no_slash, flags=re.IGNORECASE)


async def await_with_signal(coro, signal: asyncio.Event | None = None):
    """等待协程完成；signal 置位时取消该协程。"""
    if signal is None:
        return await coro
    task = asyncio.create_task(coro)

    async def _watch() -> None:
        await signal.wait()
        task.cancel()

    watcher = asyncio.create_task(_watch())
    try:
        return await task
    finally:
        watcher.cancel()
