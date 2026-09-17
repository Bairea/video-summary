"""tasks 表数据访问。与旧 TS taskRepo.ts 行为一致。"""

import json
import uuid
from datetime import datetime, timezone

from ..db import db_session
from ..types import TaskDTO, empty_artifacts


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _fallback_runtime_from_stage(stage: str | None) -> dict:
    if stage == "ready":
        return {"status": "succeeded", "retryable": False, "artifacts": empty_artifacts()}
    if stage == "failed":
        return {"status": "failed", "retryable": True, "artifacts": empty_artifacts()}
    if stage == "canceled":
        return {"status": "canceled", "retryable": False, "artifacts": empty_artifacts()}
    if stage and stage != "created":
        return {"status": "running", "retryable": False, "artifacts": empty_artifacts()}
    return {"status": "queued", "retryable": False, "artifacts": empty_artifacts()}


def derive_runtime_state_for_row(row: dict) -> dict:
    runtime_json = row.get("runtime_json")
    if not runtime_json:
        return _fallback_runtime_from_stage(row.get("stage"))
    try:
        parsed = json.loads(runtime_json)
        artifacts = parsed.get("artifacts") or {}
        return {
            "status": parsed.get("status") or "queued",
            "retryable": parsed.get("retryable", False),
            "currentStage": parsed.get("currentStage"),
            "lastCompletedStage": parsed.get("lastCompletedStage"),
            "failureStage": parsed.get("failureStage"),
            "failureCode": parsed.get("failureCode"),
            "artifacts": {**empty_artifacts(), **artifacts},
        }
    except (json.JSONDecodeError, TypeError):
        return _fallback_runtime_from_stage(row.get("stage"))


def _row_to_dto(row: dict) -> TaskDTO:
    runtime = derive_runtime_state_for_row(row)
    return {
        "id": row["id"],
        "url": row["url"],
        "platform": row["platform"],
        "title": row["title"] or None,
        "durationSec": row["duration_sec"],
        "stage": row["stage"],
        "status": runtime["status"],
        "progress": row["progress"],
        "error": row["error"] or None,
        "currentStage": runtime["currentStage"],
        "lastCompletedStage": runtime["lastCompletedStage"],
        "failureStage": runtime["failureStage"],
        "failureCode": runtime["failureCode"],
        "retryable": runtime["retryable"],
        "artifacts": runtime["artifacts"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def create_task(req: dict, platform: str) -> TaskDTO:
    now = _now()
    task_id = str(uuid.uuid4())
    with db_session() as conn:
        conn.execute(
            "INSERT INTO tasks (id, url, platform, stage, progress, pipeline_json, request_json, runtime_json, language, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (task_id, req["url"], platform, "created", 0, json.dumps(req["pipeline"]),
             json.dumps(req), json.dumps({"status": "queued", "retryable": False, "artifacts": empty_artifacts()}),
             req.get("language"), now, now),
        )
        row = dict(conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())
    return _row_to_dto(row)


def list_tasks() -> list[TaskDTO]:
    with db_session() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()]
    return [_row_to_dto(r) for r in rows]


def get_task(task_id: str) -> TaskDTO | None:
    row = get_task_row(task_id)
    return _row_to_dto(row) if row else None


def get_task_row(task_id: str) -> dict | None:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def update_task_stage(task_id: str, stage: str, opts: dict | None = None) -> None:
    opts = opts or {}
    current = get_task_row(task_id)
    current_runtime = derive_runtime_state_for_row(current) if current else {}
    now = _now()

    progress = opts["progress"] if "progress" in opts else (current["progress"] if current else None)
    error = opts["error"] if "error" in opts else (current["error"] if current else None)
    title = opts["title"] if "title" in opts else (current["title"] if current else None)
    duration_sec = opts["durationSec"] if "durationSec" in opts else (current["duration_sec"] if current else None)

    runtime = {
        **current_runtime,
        **opts.get("runtime", {}),
        "artifacts": {
            **empty_artifacts(),
            **(current_runtime.get("artifacts") or {}),
            **((opts.get("runtime") or {}).get("artifacts") or {}),
        },
    }

    with db_session() as conn:
        conn.execute(
            "UPDATE tasks SET stage = ?, progress = ?, error = ?, title = ?, duration_sec = ?, runtime_json = ?, updated_at = ? WHERE id = ?",
            (stage, progress, error, title, duration_sec, json.dumps(runtime), now, task_id),
        )


def mark_task_canceled(task_id: str) -> None:
    update_task_stage(task_id, "canceled", {
        "progress": None,
        "error": None,
        "runtime": {"status": "canceled", "retryable": False},
    })


def get_task_request(task_id: str) -> dict | None:
    row = get_task_row(task_id)
    if not row or not row.get("request_json"):
        return None
    try:
        return json.loads(row["request_json"])
    except json.JSONDecodeError:
        return None


def reset_task_for_retry(task_id: str) -> None:
    """重置失败/取消状态以便重试。保留 artifacts，让 run_pipeline 跳过已完成阶段（续跑）。"""
    row = get_task_row(task_id)
    if not row:
        return
    runtime = derive_runtime_state_for_row(row)
    now = _now()
    with db_session() as conn:
        conn.execute(
            "UPDATE tasks SET stage = ?, progress = ?, error = ?, runtime_json = ?, updated_at = ? WHERE id = ?",
            ("created", 0, None, json.dumps({
                **runtime,
                "status": "queued",
                "currentStage": None,
                "lastCompletedStage": None,
                "failureStage": None,
                "failureCode": None,
                "retryable": False,
                "artifacts": runtime.get("artifacts") or empty_artifacts(),
            }), now, task_id),
        )


def delete_task(task_id: str) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM transcript_segments WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM summaries WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM mindmaps WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM qa_messages WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
