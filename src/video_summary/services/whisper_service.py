"""faster-whisper 本地转写（替代原 mlx-whisper 链路）。"""

import asyncio
import logging

from ..paths import resolve_models_dir
from .settings_sync import load_settings_sync

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "large-v3-turbo"
_model_cache: dict[str, object] = {}


def _load_model(model_size: str, download_root: str):
    from faster_whisper import WhisperModel
    if model_size not in _model_cache:
        logger.info("loading faster-whisper model %s (download_root=%s)", model_size, download_root)
        _model_cache[model_size] = WhisperModel(model_size, device="auto", compute_type="int8",
                                                download_root=download_root)
    return _model_cache[model_size]


def _transcribe_sync(audio_path: str, model_size: str, download_root: str, language: str | None) -> list[dict]:
    model = _load_model(model_size, download_root)
    segments, _ = model.transcribe(audio_path, language=language, vad_filter=True)
    result = []
    for segment in segments:
        text = (segment.text or "").strip()
        if text:
            result.append({
                "startMs": round(segment.start * 1000),
                "endMs": round(segment.end * 1000),
                "text": text,
            })
    if not result:
        raise RuntimeError("本地 Whisper 未返回有效字幕片段")
    return result


def format_whisper_error(error: Exception) -> str:
    message = str(error)
    if isinstance(error, OSError):
        return f"模型下载或音频读取失败：{message}（请检查网络并重试，或执行 vsum models download）"
    return message


async def transcribe_with_whisper(
    audio_path: str,
    language: str | None = None,
    signal: asyncio.Event | None = None,
) -> list[dict]:
    settings = await asyncio.to_thread(load_settings_sync)
    model_size = settings["ai"].get("transcriptionModel") or DEFAULT_MODEL
    download_root = str(resolve_models_dir())
    try:
        return await asyncio.to_thread(_transcribe_sync, audio_path, model_size, download_root, language)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"本地 Whisper 转写失败：{format_whisper_error(e)}"[:320]) from e
