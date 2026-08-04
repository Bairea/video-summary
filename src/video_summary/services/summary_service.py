"""摘要生成。与旧 TS summaryService.ts 行为一致。"""

import asyncio

from ..lib.subtitle_parse import segments_to_text
from .openai_compat import chat_complete

SUMMARY_SYSTEM_PROMPT = (
    "你是一个视频学习助手。请根据给定字幕内容，输出结构化中文摘要，包含：一句话摘要、章节要点（分点）、行动项、关键词（#标签）。输出 Markdown。"
)
MERGE_SYSTEM_PROMPT = (
    "你将收到多段摘要草稿。请合并去重，形成一份最终 Markdown，总体保持精炼但信息密度高，包含：一句话摘要、章节要点、行动项、关键词。"
)


def chunk_text(text: str, max_chars: int) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunks.append(text[start:end])
        start = end
    return [c for c in chunks if c.strip()]


async def generate_summary(segments: list[dict], signal: asyncio.Event | None = None) -> str:
    text = segments_to_text(segments)
    chunks = chunk_text(text, 9000)

    partials: list[str] = []
    for c in chunks[:6]:
        out = await chat_complete([
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": c},
        ], signal=signal)
        partials.append(out)

    if len(partials) == 1:
        return partials[0]

    merged = await chat_complete([
        {"role": "system", "content": MERGE_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n---\n\n".join(partials)},
    ], signal=signal)
    return merged
