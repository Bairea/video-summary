"""SRT/VTT 解析与字幕文本拼接。"""

import re

from ..types import TranscriptSegment


def time_to_ms(s: str) -> int:
    m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)", s)
    if not m:
        return 0
    hh, mm, ss, frac = int(m[1]), int(m[2]), int(m[3]), m[4]
    ms = int(frac.ljust(3, "0")[:3])
    return ((hh * 60 + mm) * 60 + ss) * 1000 + ms


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


def parse_srt(content: str) -> list[TranscriptSegment]:
    blocks = [b.strip() for b in content.replace("\r", "").split("\n\n") if b.strip()]
    segments: list[TranscriptSegment] = []
    for block in blocks:
        lines = [l for l in block.split("\n") if l]
        if len(lines) < 2:
            continue
        time_line_idx = 0 if "-->" in lines[0] else 1
        if time_line_idx >= len(lines):
            continue
        m = re.match(r"(.+?)\s*-->\s*(.+)", lines[time_line_idx])
        if not m:
            continue
        start_ms = time_to_ms(m[1].strip())
        end_ms = time_to_ms(m[2].strip().split(" ")[0])
        text = clean_text(" ".join(lines[time_line_idx + 1:]))
        if text:
            segments.append({"startMs": start_ms, "endMs": end_ms, "text": text})
    return segments


def parse_vtt(content: str) -> list[TranscriptSegment]:
    lines = content.replace("\r", "").split("\n")
    segments: list[TranscriptSegment] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("WEBVTT"):
            i += 1
            continue
        time_line = line if "-->" in line else (lines[i + 1].strip() if i + 1 < len(lines) else "")
        if not time_line or "-->" not in time_line:
            i += 1
            continue
        m = re.match(r"(.+?)\s*-->\s*(.+)", time_line)
        if not m:
            i += 1
            continue
        start_ms = time_to_ms(m[1].strip())
        end_ms = time_to_ms(m[2].strip().split(" ")[0])
        i += 1 if "-->" in line else 2
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(lines[i].strip())
            i += 1
        text = clean_text(" ".join(text_lines))
        if text:
            segments.append({"startMs": start_ms, "endMs": end_ms, "text": text})
    return segments


def segments_to_text(segments: list[TranscriptSegment]) -> str:
    return "\n".join(s["text"] for s in segments)
