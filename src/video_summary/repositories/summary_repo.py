"""摘要数据访问。与旧 TS summaryRepo.ts 行为一致。"""

from datetime import datetime, timezone

from ..db import db_session


def get_summary(task_id: str) -> str | None:
    with db_session() as conn:
        row = conn.execute("SELECT markdown FROM summaries WHERE task_id = ?", (task_id,)).fetchone()
    return row["markdown"] if row else None


def upsert_summary(task_id: str, markdown: str) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    with db_session() as conn:
        conn.execute(
            "INSERT INTO summaries (task_id, markdown, created_at) VALUES (?, ?, ?)"
            " ON CONFLICT(task_id) DO UPDATE SET markdown = excluded.markdown, created_at = excluded.created_at",
            (task_id, markdown, now),
        )
