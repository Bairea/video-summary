"""Markmap 导图生成。与旧 TS mindmapService.ts 行为一致。"""

import asyncio
import re

from ..lib.subtitle_parse import segments_to_text
from .openai_compat import chat_complete

MINMAP_SYSTEM_PROMPT = (
    "你是一个知识整理助手。根据字幕生成适用于 Markmap 的 Markdown 导图。仅输出 Markdown，可包含 ```markdown 代码块。要求：第一行是一级标题；后续使用二级标题和简洁列表项；不要输出 Mermaid 语法。"
)

EMPTY_MINMAP = "# 视频要点\n\n- 暂无内容"


def extract_markdown_fence(raw: str) -> str | None:
    m = re.search(r"```(?:markdown|md)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    return m.group(1).strip() if m else None


def normalize_line(line: str) -> str:
    line = re.sub(r"^\s*[-*+]\s*", "", line)
    line = re.sub(r"^\s*\d+[.)]\s*", "", line)
    line = re.sub(r"^\s*#+\s*", "", line)
    return line.strip()


def normalize_markmap_markdown(raw: str) -> str:
    extracted = extract_markdown_fence(raw) or raw
    cleaned = extracted.strip()
    if not cleaned:
        return EMPTY_MINMAP

    if re.search(r"^#", cleaned, re.MULTILINE):
        return cleaned

    lines = [normalize_line(l) for l in cleaned.splitlines() if l.strip()]
    lines = [l for l in lines if l][:12]
    if not lines:
        return EMPTY_MINMAP
    return f"# 视频要点\n\n" + "\n".join(f"- {line}" for line in lines)


async def generate_mindmap(segments: list[dict], signal: asyncio.Event | None = None) -> str:
    text = segments_to_text(segments)
    clipped = text[:12000]

    out = await chat_complete([
        {"role": "system", "content": MINMAP_SYSTEM_PROMPT},
        {"role": "user", "content": clipped},
    ], signal=signal)

    return normalize_markmap_markdown(out)
