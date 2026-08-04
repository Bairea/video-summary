"""路径解析：数据目录（XDG）、任务目录、模型目录。"""

import os
from pathlib import Path

_task_output_dir_override: Path | None = None


def set_task_output_dir(output_dir: str | None) -> None:
    global _task_output_dir_override
    normalized = output_dir.strip() if output_dir else ""
    _task_output_dir_override = Path(normalized).resolve() if normalized else None


def resolve_data_dir() -> Path:
    configured = os.environ.get("VIDEO_SUMMARY_DATA_DIR", "").strip()
    if configured:
        return Path(configured).resolve()
    return Path.home() / ".local" / "share" / "video-summary"


def resolve_db_path() -> Path:
    return resolve_data_dir() / "app.db"


def resolve_models_dir() -> Path:
    return resolve_data_dir() / "models"


def resolve_tasks_dir(output_dir: str | None = None) -> Path:
    target = output_dir or _task_output_dir_override
    if target:
        return Path(target).resolve()
    return resolve_data_dir() / "tasks"


def resolve_task_dir(task_id: str, output_dir: str | None = None) -> Path:
    return resolve_tasks_dir(output_dir) / task_id


def resolve_static_dir() -> Path | None:
    """前端构建产物目录：环境变量优先，其次包内 static/。"""
    configured = os.environ.get("VIDEO_SUMMARY_STATIC_DIR", "").strip()
    if configured:
        p = Path(configured).resolve()
        return p if p.is_dir() else None
    pkg_static = Path(__file__).resolve().parent / "static"
    return pkg_static if pkg_static.is_dir() else None
