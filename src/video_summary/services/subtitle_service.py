"""字幕获取（平台字幕优先，本地 ASR 兜底）。与旧 TS subtitleService.ts 行为一致。"""

import asyncio
import json
import logging

from ..lib.subtitle_format import segments_to_srt, segments_to_vtt
from ..lib.subtitle_parse import parse_srt, parse_vtt, segments_to_text
from .file_store import ensure_task_dir, task_file
from .settings_sync import load_settings_sync
from .whisper_service import transcribe_with_whisper
from .ytdlp_service import download_media, download_subtitles

logger = logging.getLogger(__name__)


async def _write_subtitle_artifacts(task_id: str, segments: list[dict], source: str) -> dict:
    srt = segments_to_srt(segments)
    vtt = segments_to_vtt(segments)
    for name, content in [
        ("subtitles.srt", srt),
        ("subtitles.vtt", vtt),
        ("subtitles.txt", segments_to_text(segments)),
        ("subtitles.json", json.dumps(segments)),
    ]:
        task_file(task_id, name).write_text(content, "utf-8")
    return {
        "source": source,
        "segments": segments,
        "formats": ["srt", "vtt", "txt", "json"],
        "hasSrt": True,
        "hasVtt": True,
    }


def normalize_asr_language(language: str | None) -> str | None:
    if not language:
        return None
    if "," in language:
        return None
    first = language.strip()
    if not first:
        return None
    if first.lower().startswith("zh"):
        return "zh"
    if len(first) >= 2:
        return first[:2].lower()
    return None


def find_first_by_ext(dir_path, exts: list[str]):
    import os
    items = os.listdir(dir_path)
    for ext in exts:
        for f in items:
            if f.lower().endswith(ext):
                return dir_path / f
    return None


def find_audio_file(dir_path):
    import os
    for f in os.listdir(dir_path):
        if f.startswith("audio.") and not f.endswith(".part"):
            return dir_path / f
    return None


async def fetch_subtitles(task_id: str, url: str, language: str | None = None,
                          signal: asyncio.Event | None = None) -> dict:
    dir_path = ensure_task_dir(task_id)
    await download_subtitles(url, str(dir_path), {"language": language}, signal=signal)

    srt_path = find_first_by_ext(dir_path, [".srt"])
    vtt_path = find_first_by_ext(dir_path, [".vtt"])

    segments: list[dict] = []
    has_srt = False
    has_vtt = False

    if srt_path is not None:
        content = srt_path.read_text("utf-8")
        segments = parse_srt(content)
        task_file(task_id, "subtitles.srt").write_text(content, "utf-8")
        has_srt = True

    if not segments and vtt_path is not None:
        content = vtt_path.read_text("utf-8")
        segments = parse_vtt(content)
        task_file(task_id, "subtitles.vtt").write_text(content, "utf-8")
        has_vtt = True

    if segments:
        if not has_srt:
            task_file(task_id, "subtitles.srt").write_text(segments_to_srt(segments), "utf-8")
            has_srt = True
        if not has_vtt:
            task_file(task_id, "subtitles.vtt").write_text(segments_to_vtt(segments), "utf-8")
            has_vtt = True
        task_file(task_id, "subtitles.txt").write_text(segments_to_text(segments), "utf-8")
        task_file(task_id, "subtitles.json").write_text(json.dumps(segments), "utf-8")
        return {
            "source": "platform",
            "segments": segments,
            "formats": ["srt", "vtt", "txt", "json"],
            "hasSrt": has_srt,
            "hasVtt": has_vtt,
        }

    settings = await asyncio.to_thread(load_settings_sync)
    if not settings["ai"].get("asrEnabled", True):
        raise RuntimeError("未获取到平台字幕，且已关闭“无字幕自动 ASR”")

    await download_media(url, str(dir_path), {"audioOnly": True, "quality": "best"}, signal=signal)
    audio_path = find_audio_file(dir_path)
    if audio_path is None:
        raise RuntimeError("平台字幕不可用，且 ASR 音频下载失败")

    asr_segments = await transcribe_with_whisper(
        str(audio_path),
        language=normalize_asr_language(language),
        signal=signal,
    )
    return await _write_subtitle_artifacts(task_id, asr_segments, "asr")


async def export_subtitles(task_id: str, format: str) -> dict:
    content_types = {
        "srt": "application/x-subrip",
        "vtt": "text/vtt",
        "txt": "text/plain; charset=utf-8",
        "json": "application/json; charset=utf-8",
    }
    path = task_file(task_id, f"subtitles.{format}")
    body = await asyncio.to_thread(path.read_text, "utf-8")
    return {"fileName": f"subtitles.{format}", "contentType": content_types[format], "body": body}
