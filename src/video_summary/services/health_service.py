"""健康检查。检查项与旧 TS healthService.js 对齐：dataDir/aiConfig/ytDlp/markmap/localWhisper/whisperWeights/cookies。"""

import asyncio
import importlib.util
import shutil
from datetime import datetime, timezone

from ..paths import resolve_data_dir, resolve_models_dir, resolve_static_dir
from .settings_sync import load_settings_sync


def _file_exists(p) -> bool:
    from pathlib import Path
    return Path(p).is_file()


def _get_ai_missing_fields(settings: dict) -> list[str]:
    missing = []
    from .openai_compat import resolve_ai_settings
    resolved = resolve_ai_settings(settings)
    if not resolved["baseUrl"]:
        missing.append("baseUrl")
    if not resolved["apiKey"]:
        missing.append("apiKey")
    if not resolved["model"]:
        missing.append("model")
    return missing


def _detect_ytdlp(settings: dict) -> dict:
    configured = (settings.get("download", {}).get("ytdlpPath") or "").strip()
    if configured:
        if not _file_exists(configured):
            return {"ok": False, "detail": f"设置中的路径不存在：{configured}", "path": configured, "source": "configured"}
        return {"ok": True, "detail": f"使用设置中的路径：{configured}", "path": configured, "source": "configured"}

    if shutil.which("yt-dlp"):
        return {"ok": True, "detail": "使用系统 PATH 中的 yt-dlp", "path": "yt-dlp", "source": "system"}

    if importlib.util.find_spec("yt_dlp"):
        return {"ok": True, "detail": "使用 pip 安装的 yt-dlp（python -m yt_dlp）", "source": "pip"}
    return {"ok": False, "detail": "未检测到可用的 yt-dlp（pip 依赖缺失，请重装 video-summary 或设置 yt-dlp 路径）", "source": "missing"}


def _detect_asr() -> dict:
    """检测 ASR 引擎：Apple Silicon 用 mlx-whisper，其他用 whisper.cpp CLI。"""
    import platform
    import sys

    if sys.platform == "darwin" and platform.machine() == "arm64":
        if importlib.util.find_spec("mlx_whisper"):
            return {"ok": True, "detail": "mlx-whisper 引擎已就绪 (Apple Silicon)"}
        return {"ok": False, "detail": "未检测到 mlx-whisper 运行时（pip 依赖缺失，请重装 video-summary）"}

    # 非 Apple Silicon：检查 whisper.cpp CLI
    if shutil.which("whisper-cpp") or shutil.which("whisper.cpp"):
        return {"ok": True, "detail": "whisper.cpp CLI 已就绪"}
    # 检查常见安装位置
    for p in ["/usr/local/bin/whisper-cpp", "/opt/homebrew/bin/whisper-cpp"]:
        from pathlib import Path
        if Path(p).is_file():
            return {"ok": True, "detail": f"whisper.cpp CLI 已就绪: {p}"}
    return {"ok": False, "detail": "未检测到 whisper.cpp 可执行文件（请安装 whisper.cpp 并添加到 PATH）"}


def _detect_models() -> dict:
    models_dir = resolve_models_dir()
    if models_dir.exists() and any(models_dir.iterdir()):
        return {"ok": True, "detail": f"已检测到模型目录：{models_dir}", "path": str(models_dir)}
    return {"ok": False, "detail": f"未检测到模型文件：{models_dir}（运行 vsum models --download 下载）", "path": str(models_dir)}


async def get_health_snapshot() -> dict:
    settings = await asyncio.to_thread(load_settings_sync)
    data_dir = resolve_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    ai_missing = _get_ai_missing_fields(settings)
    cookies_path = (settings.get("download", {}).get("cookiesPath") or "").strip() or str(data_dir / "cookies.txt")

    ytdlp = _detect_ytdlp(settings)
    asr = _detect_asr()
    models = _detect_models()
    static_dir = resolve_static_dir()

    checks = {
        "dataDir": {
            "ok": True,
            "label": "数据目录",
            "required": True,
            "detail": f"使用目录：{data_dir}",
            "path": str(data_dir),
        },
        "aiConfig": {
            "ok": len(ai_missing) == 0,
            "label": "AI 摘要配置",
            "required": True,
            "detail": "Base URL / API Key / Model 已配置，可继续用“测试 AI”验证连通性" if not ai_missing
                      else f"缺少字段：{', '.join(ai_missing)}",
            "missing": ai_missing,
        },
        "ytDlp": {
            "ok": ytdlp["ok"],
            "label": "yt-dlp",
            "required": True,
            "detail": ytdlp["detail"],
            "path": ytdlp.get("path"),
            "source": ytdlp.get("source"),
        },
        "markmap": {
            "ok": static_dir is not None,
            "label": "前端构建 (Markmap)",
            "required": True,
            "detail": f"使用构建产物：{static_dir}" if static_dir else "未检测到前端构建产物（在仓库目录运行 npm run build 后可用）",
            "path": str(static_dir) if static_dir else None,
        },
        "localWhisper": {
            "ok": asr["ok"],
            "label": "本地 ASR",
            "required": False,
            "detail": asr["detail"],
        },
        "whisperWeights": {
            "ok": models["ok"],
            "label": "ASR 模型权重",
            "required": False,
            "detail": models["detail"],
            "path": models.get("path"),
        },
        "cookies": {
            "ok": _file_exists(cookies_path),
            "label": "cookies.txt",
            "required": False,
            "detail": f"已检测到：{cookies_path}" if _file_exists(cookies_path) else f"未检测到：{cookies_path}",
            "path": cookies_path,
        },
    }

    checked_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    required_failures = [c for c in checks.values() if c["required"] and not c["ok"]]
    if required_failures:
        return {
            "checkedAt": checked_at,
            "ok": False,
            "status": "needs_attention",
            "summary": "仍需处理：" + "、".join(c["label"] for c in required_failures),
            "checks": checks,
        }
    return {
        "checkedAt": checked_at,
        "ok": True,
        "status": "ready",
        "summary": "运行基线已满足",
        "checks": checks,
    }
