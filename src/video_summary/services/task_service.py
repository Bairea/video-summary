"""任务流水线编排（CLI 同步编排 / Web 异步编排共用）。与旧 TS taskService.ts 行为一致。"""

import asyncio
import json
import re
from urllib.parse import urlparse

from ..repositories import mindmap_repo, summary_repo, task_repo, transcript_repo
from ..types import empty_artifacts
from .file_store import ensure_task_dir, remove_task_dir, task_file
from .job_queue import JobCancelled, JobQueue
from .mindmap_service import generate_mindmap
from .settings_sync import load_settings_sync
from .subtitle_service import fetch_subtitles
from .summary_service import generate_summary
from .ytdlp_service import download_media, dump_info

EXECUTION_STAGE_ORDER = ["parse", "download", "subtitles", "summary", "mindmap", "qaIndex"]


def detect_platform(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return "unknown"
    host = host.lower()
    if "bilibili.com" in host or host == "b23.tv":
        return "bilibili"
    if "youtube.com" in host or host == "youtu.be":
        return "youtube"
    return "unknown"


def _build_running_runtime(current_stage: str, last_completed_stage: str | None, artifacts) -> dict:
    return {
        "status": "running",
        "currentStage": current_stage,
        "lastCompletedStage": last_completed_stage,
        "retryable": False,
        "artifacts": artifacts,
    }


def _is_abort_like_error(error: BaseException, signal: asyncio.Event) -> bool:
    if signal.is_set():
        return True
    return bool(re.search(r"abort|aborted|canceled", str(error), re.IGNORECASE))


async def _aborted(task_id: str, signal: asyncio.Event) -> bool:
    """signal 置位时标记任务取消并返回 True。"""
    if not signal.is_set():
        return False
    await asyncio.to_thread(task_repo.mark_task_canceled, task_id)
    return True


def infer_failure_code(message: str) -> str:
    if re.search(r"模型下载|模型", message):
        return "whisper_weights_missing"
    if re.search(r"Whisper|转写失败|ASR", message):
        return "whisper_runtime_missing"
    if re.search(r"cookies|风控|412|403", message, re.IGNORECASE):
        return "upstream_auth_required"
    if re.search(r"subtitle|字幕", message, re.IGNORECASE):
        return "subtitle_failed"
    return "pipeline_failed"


def infer_failure_stage(req: dict, last_completed_stage: str | None) -> str | None:
    last_index = EXECUTION_STAGE_ORDER.index(last_completed_stage) if last_completed_stage in EXECUTION_STAGE_ORDER else -1
    for stage in EXECUTION_STAGE_ORDER[last_index + 1:]:
        if req["pipeline"].get(stage):
            return stage
    return None


class TaskService:
    def __init__(self, queue: JobQueue) -> None:
        self.queue = queue

    def create(self, req: dict) -> dict:
        normalized = {
            **req,
            "pipeline": {
                **req["pipeline"],
                "subtitles": (
                    req["pipeline"].get("subtitles")
                    or req["pipeline"].get("summary")
                    or req["pipeline"].get("mindmap")
                    or req["pipeline"].get("qaIndex")
                ),
            },
        }
        platform = detect_platform(req["url"])
        settings = load_settings_sync()
        from ..paths import set_task_output_dir
        set_task_output_dir(settings["download"].get("outputDir"))
        task = task_repo.create_task(normalized, platform)
        ensure_task_dir(task["id"], settings["download"].get("outputDir"))
        self.queue.enqueue(task["id"], lambda signal: self.run_pipeline(task["id"], normalized, signal))
        self.prune_old_tasks()
        return task

    def list(self) -> list[dict]:
        return task_repo.list_tasks()

    def get(self, task_id: str) -> dict | None:
        return task_repo.get_task(task_id)

    def cancel(self, task_id: str) -> bool:
        canceled = self.queue.cancel(task_id)
        task_repo.mark_task_canceled(task_id)
        return canceled

    def remove(self, task_id: str) -> None:
        self.queue.cancel(task_id)
        task_repo.delete_task(task_id)
        remove_task_dir(task_id)

    def retry(self, task_id: str) -> dict:
        req = task_repo.get_task_request(task_id)
        if not req:
            raise RuntimeError("未找到可重试的任务请求参数")
        settings = load_settings_sync()
        from ..paths import set_task_output_dir
        set_task_output_dir(settings["download"].get("outputDir"))
        task_repo.reset_task_for_retry(task_id)
        self.queue.enqueue(task_id, lambda signal: self.run_pipeline(task_id, req, signal))
        task = task_repo.get_task(task_id)
        if not task:
            raise RuntimeError("任务不存在")
        return task

    def prune_old_tasks(self, max_tasks: int | None = None) -> None:
        """按 storage.maxTasks 清理最旧的非活动任务，保持本地存储有界。"""
        if max_tasks is None:
            settings = load_settings_sync()
            max_tasks = (settings.get("storage") or {}).get("maxTasks")
        if not max_tasks or int(max_tasks) <= 0:
            return
        tasks = task_repo.list_tasks()  # created_at 倒序
        active = {"queued", "running"}
        removable = [t for t in reversed(tasks) if t["status"] not in active]  # 最旧在前
        for t in removable[:max(0, len(tasks) - int(max_tasks))]:
            self.remove(t["id"])

    async def run_pipeline(self, task_id: str, req: dict, signal: asyncio.Event) -> None:
        settings = await asyncio.to_thread(load_settings_sync)
        from ..paths import set_task_output_dir
        set_task_output_dir(settings["download"].get("outputDir"))
        ensure_task_dir(task_id, settings["download"].get("outputDir"))

        last_completed_stage: str | None = None
        artifacts = await asyncio.to_thread(self._load_artifacts, task_id)
        # 续跑：转写稿就绪（DB 标记 + 字幕文件在盘上）时，download/subtitles 不再重跑
        transcript_ready = bool(artifacts.get("transcriptReady")) and task_file(task_id, "subtitles.json").is_file()

        try:
            if await _aborted(task_id, signal):
                return

            info: dict | None = None
            if req["pipeline"].get("parse"):
                await asyncio.to_thread(task_repo.update_task_stage, task_id, "parsing", {
                    "progress": 10, "error": None,
                    "runtime": _build_running_runtime("parse", last_completed_stage, artifacts),
                })
                info = await dump_info(req["url"], signal)
                last_completed_stage = "parse"
                await asyncio.to_thread(task_repo.update_task_stage, task_id, "parsing", {
                    "progress": 18, "error": None,
                    "title": info.get("title") or None,
                    "durationSec": round(info["duration"]) if info.get("duration") else None,
                    "runtime": _build_running_runtime("parse", last_completed_stage, artifacts),
                })

            if await _aborted(task_id, signal):
                return

            if req["pipeline"].get("download"):
                if transcript_ready:
                    # 已有转写稿：媒体只服务于转写，无需重下
                    last_completed_stage = "download"
                else:
                    await asyncio.to_thread(task_repo.update_task_stage, task_id, "downloading", {
                        "progress": 30, "error": None,
                        "runtime": _build_running_runtime("download", last_completed_stage, artifacts),
                    })
                    await download_media(req["url"], str(task_file(task_id)), {
                        "audioOnly": req["download"].get("audioOnly"),
                        "quality": req["download"].get("quality"),
                    }, signal=signal)
                    last_completed_stage = "download"
                    await asyncio.to_thread(task_repo.update_task_stage, task_id, "downloading", {
                        "progress": 45, "error": None,
                        "runtime": _build_running_runtime("download", last_completed_stage, artifacts),
                    })

            if await _aborted(task_id, signal):
                return

            if req["pipeline"].get("subtitles"):
                if transcript_ready:
                    last_completed_stage = "subtitles"
                else:
                    await asyncio.to_thread(task_repo.update_task_stage, task_id, "transcribing", {
                        "progress": 55, "error": None,
                        "runtime": _build_running_runtime("subtitles", last_completed_stage, artifacts),
                    })
                    result = await fetch_subtitles(task_id, req["url"], language=req.get("language"), signal=signal)
                    segments = result["segments"]
                    if not segments:
                        raise RuntimeError("未能获取字幕（平台无字幕或需要 Cookies/登录）")
                    await asyncio.to_thread(transcript_repo.replace_transcript, task_id, segments)
                    task_file(task_id, "subtitles.json").write_text(json.dumps(segments), "utf-8")
                    artifacts = {**artifacts, "transcriptReady": True, "subtitleFormats": result["formats"]}
                    last_completed_stage = "subtitles"
                    await asyncio.to_thread(task_repo.update_task_stage, task_id, "transcribing", {
                        "progress": 65, "error": None,
                        "runtime": _build_running_runtime("subtitles", last_completed_stage, artifacts),
                    })

            if await _aborted(task_id, signal):
                return

            if req["pipeline"].get("summary"):
                existing_summary = None
                if artifacts.get("summaryReady"):
                    existing_summary = await asyncio.to_thread(summary_repo.get_summary, task_id)
                if existing_summary:
                    last_completed_stage = "summary"
                else:
                    await asyncio.to_thread(task_repo.update_task_stage, task_id, "summarizing", {
                        "progress": 75, "error": None,
                        "runtime": _build_running_runtime("summary", last_completed_stage, artifacts),
                    })
                    segments = _load_segments_from_disk(task_id)
                    markdown = await generate_summary(segments, signal)
                    await asyncio.to_thread(summary_repo.upsert_summary, task_id, markdown)
                    artifacts = {**artifacts, "summaryReady": True}
                    last_completed_stage = "summary"
                    await asyncio.to_thread(task_repo.update_task_stage, task_id, "summarizing", {
                        "progress": 82, "error": None,
                        "runtime": _build_running_runtime("summary", last_completed_stage, artifacts),
                    })

            if await _aborted(task_id, signal):
                return

            if req["pipeline"].get("mindmap"):
                existing_mindmap = None
                if artifacts.get("mindmapReady"):
                    existing_mindmap = await asyncio.to_thread(mindmap_repo.get_mindmap, task_id)
                if existing_mindmap:
                    last_completed_stage = "mindmap"
                else:
                    await asyncio.to_thread(task_repo.update_task_stage, task_id, "mindmap", {
                        "progress": 88, "error": None,
                        "runtime": _build_running_runtime("mindmap", last_completed_stage, artifacts),
                    })
                    segments = _load_segments_from_disk(task_id)
                    mindmap = await generate_mindmap(segments, signal)
                    await asyncio.to_thread(mindmap_repo.upsert_mindmap, task_id, mindmap)
                    artifacts = {**artifacts, "mindmapReady": True}
                    last_completed_stage = "mindmap"
                    await asyncio.to_thread(task_repo.update_task_stage, task_id, "mindmap", {
                        "progress": 92, "error": None,
                        "runtime": _build_running_runtime("mindmap", last_completed_stage, artifacts),
                    })

            if await _aborted(task_id, signal):
                return

            if req["pipeline"].get("qaIndex"):
                artifacts = {**artifacts, "qaReady": artifacts["transcriptReady"]}
                last_completed_stage = "qaIndex"
                await asyncio.to_thread(task_repo.update_task_stage, task_id, "indexing", {
                    "progress": 96, "error": None,
                    "runtime": _build_running_runtime("qaIndex", last_completed_stage, artifacts),
                })

            await asyncio.to_thread(task_repo.update_task_stage, task_id, "ready", {
                "progress": 100, "error": None,
                "runtime": {
                    "status": "succeeded",
                    "currentStage": None,
                    "lastCompletedStage": last_completed_stage,
                    "failureStage": None,
                    "failureCode": None,
                    "retryable": False,
                    "artifacts": artifacts,
                },
            })
        except (JobCancelled, asyncio.CancelledError) as e:
            if isinstance(e, asyncio.CancelledError):
                raise
            await asyncio.to_thread(task_repo.mark_task_canceled, task_id)
        except Exception as e:
            if _is_abort_like_error(e, signal):
                await asyncio.to_thread(task_repo.mark_task_canceled, task_id)
                return
            message = str(e) or "Unknown error"
            await asyncio.to_thread(task_repo.update_task_stage, task_id, "failed", {
                "progress": None,
                "error": message,
                "runtime": {
                    "status": "failed",
                    "currentStage": None,
                    "lastCompletedStage": last_completed_stage,
                    "failureStage": infer_failure_stage(req, last_completed_stage),
                    "failureCode": infer_failure_code(message),
                    "retryable": True,
                    "artifacts": artifacts,
                },
            })


    def _load_artifacts(self, task_id: str) -> dict:
        """读取已持久化的阶段产物标记，供续跑判断（新任务为全空）。"""
        task = task_repo.get_task(task_id)
        return (task or {}).get("artifacts") or empty_artifacts()


def _load_segments_from_disk(task_id: str) -> list[dict]:
    return json.loads(task_file(task_id, "subtitles.json").read_text("utf-8"))


job_queue = JobQueue()
task_service = TaskService(job_queue)
