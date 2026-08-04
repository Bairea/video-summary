"""yt-dlp 子进程调用（Python 包内以 `python -m yt_dlp` 提供）。与旧 TS ytdlpService.ts 行为一致。"""

import asyncio
import json
import logging
import shutil
import sys
from urllib.parse import urlparse

from ..lib.retry import retry
from ..paths import resolve_data_dir
from .job_queue import JobCancelled
from .settings_sync import load_settings_sync

logger = logging.getLogger(__name__)

BILI_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def get_bili_workaround_args(url: str) -> list[str]:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        host = ""
    host = host.lower()
    if "bilibili.com" not in host and host != "b23.tv":
        return []
    return [
        "--user-agent", BILI_UA,
        "--add-header", "Referer:https://www.bilibili.com",
        "--add-header", "Origin:https://www.bilibili.com",
        "--add-header", "Accept-Language:zh-CN,zh;q=0.9,en;q=0.8",
        "--sleep-interval", "1",
        "--max-sleep-interval", "3",
        "--concurrent-fragments", "1",
    ]


def _file_exists(path: str) -> bool:
    from pathlib import Path
    return Path(path).is_file()


def resolve_cookies_path(configured_cookies_path: str | None, default_cookies_path: str) -> str | None:
    configured = (configured_cookies_path or "").strip()
    if configured and _file_exists(configured):
        return configured
    if _file_exists(default_cookies_path):
        return default_cookies_path
    return None


async def _probe_bin(bin_name: str) -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            bin_name, "--version", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        code = await proc.wait()
        return code == 0
    except (OSError, FileNotFoundError):
        return False


async def _probe_python_ytdlp() -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "yt_dlp", "--version",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        code = await proc.wait()
        return code == 0
    except (OSError, FileNotFoundError):
        return False


async def resolve_ytdlp_bin() -> tuple[str, str]:
    """返回 (命令, source)。source ∈ configured | system | pip。"""
    settings = await asyncio.to_thread(load_settings_sync)
    configured = (settings["download"].get("ytdlpPath") or "").strip()
    if configured:
        if not _file_exists(configured):
            raise RuntimeError(f"设置中的 yt-dlp 路径不存在：{configured}")
        return configured, "configured"
    if shutil.which("yt-dlp") and await _probe_bin("yt-dlp"):
        return "yt-dlp", "system"
    if await _probe_python_ytdlp():
        return f"{sys.executable} -m yt_dlp", "pip"
    raise RuntimeError("未检测到可用的 yt-dlp（pip 依赖缺失，请重装 video-summary 或设置 yt-dlp 路径）")


async def _get_common_args() -> list[str]:
    settings = await asyncio.to_thread(load_settings_sync)
    args: list[str] = []
    proxy = (settings["download"].get("proxy") or "").strip()
    if proxy:
        args += ["--proxy", proxy]
    cookies_path = resolve_cookies_path(
        settings["download"].get("cookiesPath"),
        str(resolve_data_dir() / "cookies.txt"),
    )
    if cookies_path:
        args += ["--cookies", cookies_path]
    args += ["--retries", "5", "--fragment-retries", "5", "--extractor-retries", "5",
             "--socket-timeout", "15", "--retry-sleep", "1:3"]
    return args


async def _run(bin_name: str, args: list[str], *, cwd: str | None = None,
               signal: asyncio.Event | None = None) -> dict:
    parts = bin_name.split(" ")
    proc = await asyncio.create_subprocess_exec(
        *parts, *args, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )

    def abort() -> None:
        if proc.returncode is None:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass

    watcher: asyncio.Task | None = None
    if signal is not None:
        async def _watch() -> None:
            await signal.wait()
            abort()
        watcher = asyncio.create_task(_watch())

    try:
        stdout_bytes, stderr_bytes = await proc.communicate()
    finally:
        if watcher is not None:
            watcher.cancel()

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        tail = " | ".join([l for l in stderr.splitlines() if l][-8:]) or "unknown"
        raise RuntimeError(f"yt-dlp failed ({proc.returncode}): {tail}")
    return {"stdout": stdout, "stderr": stderr}


async def dump_info(url: str, signal: asyncio.Event | None = None) -> dict:
    bin_name, _ = await resolve_ytdlp_bin()
    common = await _get_common_args()
    workaround = get_bili_workaround_args(url)
    result = await retry(
        lambda attempt: _run(bin_name, ["--dump-single-json", "--no-warnings", "--no-playlist", *common, *workaround, url],
                             signal=signal),
        retries=2, base_delay_ms=300, max_delay_ms=1200, signal=signal,
    )
    return json.loads(result["stdout"])


async def download_media(
    url: str, out_dir: str,
    opts: dict | None = None, signal: asyncio.Event | None = None,
) -> None:
    opts = opts or {}
    bin_name, _ = await resolve_ytdlp_bin()
    common = await _get_common_args()
    workaround = get_bili_workaround_args(url)
    out_dir_path = out_dir
    from pathlib import Path
    Path(out_dir_path).mkdir(parents=True, exist_ok=True)

    out_tpl = str(Path(out_dir_path) / ("audio.%(ext)s" if opts.get("audioOnly") else "video.%(ext)s"))
    args = ["--no-warnings", "--no-playlist", *common, *workaround, "-o", out_tpl]

    if opts.get("audioOnly"):
        args += ["-f", "bestaudio/best"]
    elif opts.get("quality") and opts["quality"] != "best":
        h = str(opts["quality"]).replace("p", "")
        args += ["-f", f"best[height<={h}]/best"]
    else:
        args += ["-f", "best"]

    args.append(url)
    try:
        await retry(
            lambda attempt: _run(bin_name, args, cwd=out_dir_path, signal=signal),
            retries=2, base_delay_ms=600, max_delay_ms=2500, signal=signal,
        )
    except JobCancelled:
        raise
    except RuntimeError as e:
        msg = str(e)
        if "HTTP Error 412" in msg or "Precondition Failed" in msg:
            raise RuntimeError("B 站请求被风控(412)：请更新 cookies.txt（登录态），并建议开启代理/降低请求频率后重试") from e
        raise


async def download_subtitles(
    url: str, out_dir: str,
    opts: dict | None = None, signal: asyncio.Event | None = None,
) -> None:
    opts = opts or {}
    bin_name, _ = await resolve_ytdlp_bin()
    common = await _get_common_args()
    workaround = get_bili_workaround_args(url)
    from pathlib import Path
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    out_tpl = str(Path(out_dir) / "video.%(ext)s")
    args = [
        "--no-warnings", "--no-playlist", *common, *workaround,
        "--skip-download", "--write-subs", "--write-auto-subs", "--sub-format", "vtt", "-o", out_tpl,
    ]
    language = opts.get("language")
    if language:
        args += ["--sub-langs", language]
    args.append(url)
    try:
        await retry(
            lambda attempt: _run(bin_name, args, cwd=out_dir, signal=signal),
            retries=3, base_delay_ms=800, max_delay_ms=4000, signal=signal,
        )
    except JobCancelled:
        raise
    except RuntimeError as e:
        msg = str(e)
        if re_search_sign_in(msg):
            raise RuntimeError("字幕拉取失败：可能需要 cookies.txt（B 站登录态）或代理") from e
        if "HTTP Error 412" in msg or "Precondition Failed" in msg:
            raise RuntimeError("B 站请求被风控(412)：请更新 cookies.txt（登录态），并建议开启代理/降低请求频率后重试") from e
        raise


def re_search_sign_in(msg: str) -> bool:
    import re
    return bool(re.search(r"sign in|login|cookies|403|forbidden", msg, re.IGNORECASE))
