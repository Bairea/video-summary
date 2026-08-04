"""导图数据访问。与旧 TS mindmapRepo.ts 行为一致。"""

from datetime import datetime, timezone

from ..db import db_session


def get_mindmap(task_id: str) -> str | None:
    with db_session() as conn:
        row = conn.execute("SELECT mermaid FROM mindmaps WHERE task_id = ?", (task_id,)).fetchone()
    return row["mermaid"] if row else None


def upsert_mindmap(task_id: str, content: str) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    with db_session() as conn:
        conn.execute(
            "INSERT INTO mindmaps (task_id, mermaid, created_at) VALUES (?, ?, ?)"
            " ON CONFLICT(task_id) DO UPDATE SET mermaid = excluded.mermaid, created_at = excluded.created_at",
            (task_id, content, now),
        )
