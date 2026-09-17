"""本地转写：Apple Silicon 用 mlx-whisper，其他平台用 whisper.cpp CLI。"""

import asyncio
import json
import logging
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from ..paths import resolve_models_dir
from .settings_sync import load_settings_sync

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "large-v3"
_MODEL_MAP_MLX = {
    "tiny": "mlx-community/whisper-tiny-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
}
_MODEL_MAP_MLX_MODELSCOPE = {
    "tiny": "MLX-Community/whisper-tiny-mlx",
    "base": "MLX-Community/whisper-base-mlx",
    "small": "MLX-Community/whisper-small-mlx",
    "medium": "MLX-Community/whisper-medium-mlx",
    "large-v3": "MLX-Community/whisper-large-v3-mlx",
}
_MODEL_MAP_WHISPER_CPP = {
    "tiny": "ggml-tiny.bin",
    "base": "ggml-base.bin",
    "small": "ggml-small.bin",
    "medium": "ggml-medium.bin",
    "large-v3": "ggml-large-v3.bin",
}


def _is_apple_silicon() -> bool:
    """检测是否为 Apple Silicon (M1/M2/M3/M4)。"""
    if sys.platform != "darwin":
        return False
    # macOS 上进一步检查架构
    return platform.machine() == "arm64"


def _get_whisper_cpp_path() -> str | None:
    """查找 whisper.cpp 可执行文件路径。"""
    for name in ("whisper-cpp", "whisper.cpp", "main"):
        path = shutil.which(name)
        if path:
            return path
    # 常见安装位置
    for p in [
        "/usr/local/bin/whisper-cpp",
        "/usr/local/bin/whisper.cpp",
        "/opt/homebrew/bin/whisper-cpp",
        Path.home() / ".local/bin/whisper-cpp",
    ]:
        if Path(p).is_file():
            return str(p)
    return None


def _transcribe_mlx(audio_path: str, model_size: str, language: str | None) -> list[dict]:
    """mlx-whisper 转写（Apple Silicon 专用），HuggingFace 失败时降级到 ModelScope。"""
    import mlx_whisper

    hf_repo = _MODEL_MAP_MLX.get(model_size, _MODEL_MAP_MLX["large-v3"])
    try:
        result = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo=hf_repo,
            language=language,
        )
    except Exception as hf_error:
        logger.warning("HuggingFace 下载失败: %s，尝试 ModelScope", hf_error)
        ms_repo = _MODEL_MAP_MLX_MODELSCOPE.get(model_size, _MODEL_MAP_MLX_MODELSCOPE["large-v3"])
        try:
            result = mlx_whisper.transcribe(
                audio_path,
                path_or_hf_repo=ms_repo,
                language=language,
            )
        except Exception as ms_error:
            raise RuntimeError(f"HuggingFace 和 ModelScope 均下载失败: {hf_error}; {ms_error}") from ms_error

    segments = []
    for seg in result.get("segments", []):
        text = (seg.get("text") or "").strip()
        if text:
            segments.append({
                "startMs": round(seg.get("start", 0) * 1000),
                "endMs": round(seg.get("end", 0) * 1000),
                "text": text,
            })
    if not segments:
        raise RuntimeError("mlx-whisper 未返回有效字幕片段")
    return segments


def _download_whisper_cpp_model(model_size: str, model_path: Path) -> None:
    """下载 whisper.cpp 模型，HuggingFace 失败时降级到 ModelScope。"""
    filename = _MODEL_MAP_WHISPER_CPP.get(model_size, _MODEL_MAP_WHISPER_CPP["large-v3"])
    hf_url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{filename}"
    ms_url = f"https://modelscope.cn/models/khulnasoft/whisper.cpp/resolve/main/{filename}"

    import urllib.request
    import urllib.error

    def _download(url: str) -> bool:
        try:
            logger.info("下载模型: %s -> %s", url, model_path)
            model_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, model_path)
            return True
        except Exception as e:
            logger.warning("下载失败: %s: %s", url, e)
            return False

    if _download(hf_url):
        return
    logger.warning("HuggingFace 下载失败，尝试 ModelScope")
    if _download(ms_url):
        return
    raise RuntimeError(f"模型下载失败: HuggingFace 和 ModelScope 均不可用 ({model_size})")


def _transcribe_whisper_cpp(audio_path: str, model_size: str, language: str | None) -> list[dict]:
    """whisper.cpp CLI 转写（非 Apple Silicon 平台）。"""
    whisper_cpp = _get_whisper_cpp_path()
    if not whisper_cpp:
        raise RuntimeError("未找到 whisper.cpp 可执行文件，请安装 whisper.cpp 并添加到 PATH")

    models_dir = resolve_models_dir()
    filename = _MODEL_MAP_WHISPER_CPP.get(model_size, _MODEL_MAP_WHISPER_CPP["large-v3"])
    model_path = models_dir / filename
    if not model_path.is_file():
        _download_whisper_cpp_model(model_size, model_path)

    cmd = [
        whisper_cpp,
        "-f", audio_path,
        "-m", str(model_path),
        "-oj",  # JSON 输出
        "-nt",  # 不打印时间戳
    ]
    if language:
        cmd.extend(["-l", language[:2]])

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    # whisper.cpp 输出 JSON 文件在音频文件同目录，名为 audio.json
    json_path = Path(audio_path).with_suffix(".json")
    if not json_path.is_file():
        raise RuntimeError(f"whisper.cpp 未生成 JSON 输出: {json_path}")

    data = json.loads(json_path.read_text("utf-8"))
    segments = []
    for seg in data.get("transcription", []):
        text = (seg.get("text") or "").strip()
        if text:
            segments.append({
                "startMs": seg.get("timestamps", {}).get("from", 0) * 1000,
                "endMs": seg.get("timestamps", {}).get("to", 0) * 1000,
                "text": text,
            })
    json_path.unlink(missing_ok=True)
    if not segments:
        raise RuntimeError("whisper.cpp 未返回有效字幕片段")
    return segments


async def transcribe_with_whisper(
    audio_path: str,
    language: str | None = None,
    signal: asyncio.Event | None = None,
) -> list[dict]:
    """本地转写：Apple Silicon 用 mlx-whisper，其他用 whisper.cpp CLI。"""
    settings = await asyncio.to_thread(load_settings_sync)
    model_size = settings["ai"].get("transcriptionModel") or DEFAULT_MODEL

    try:
        if _is_apple_silicon():
            logger.info("使用 mlx-whisper 转写 (Apple Silicon)")
            return await asyncio.to_thread(_transcribe_mlx, audio_path, model_size, language)
        else:
            logger.info("使用 whisper.cpp CLI 转写")
            return await asyncio.to_thread(_transcribe_whisper_cpp, audio_path, model_size, language)
    except Exception as e:
        raise RuntimeError(f"本地转写失败: {e}") from e
