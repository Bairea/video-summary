"""问答消息数据访问。与旧 TS qaRepo.ts 行为一致。"""

import json
import uuid
from datetime import datetime, timezone

from ..db import db_session


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_meta(row: dict) -> dict:
    if not row.get("metadata_json"):
        return {}
    try:
        return json.loads(row["metadata_json"])
    except json.JSONDecodeError:
        return {}


def append_message(task_id: str, role: str, content: str, meta: dict | None = None) -> None:
    with db_session() as conn:
        conn.execute(
            "INSERT INTO qa_messages (id, task_id, role, content, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), task_id, role, content, json.dumps(meta) if meta else None, _now()),
        )


def list_messages(task_id: str) -> list[dict]:
    with db_session() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, role, content, metadata_json, created_at FROM qa_messages WHERE task_id = ? ORDER BY created_at ASC",
            (task_id,),
        ).fetchall()]
    result = []
    for r in rows:
        meta = _parse_meta(r)
        result.append({
            "id": r["id"],
            "role": r["role"],
            "content": r["content"],
            "createdAt": r["created_at"],
            "citations": meta.get("citations"),
            "insufficientEvidence": meta.get("insufficientEvidence"),
        })
    return result
