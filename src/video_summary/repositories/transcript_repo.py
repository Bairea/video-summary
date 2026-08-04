"""字幕段数据访问。与旧 TS transcriptRepo.ts 行为一致。"""

import uuid

from ..db import db_session


def replace_transcript(task_id: str, segments: list[dict]) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM transcript_segments WHERE task_id = ?", (task_id,))
        for idx, seg in enumerate(segments):
            conn.execute(
                "INSERT INTO transcript_segments (id, task_id, start_ms, end_ms, text, idx) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), task_id, seg["startMs"], seg["endMs"], seg["text"], idx),
            )


def get_transcript(task_id: str) -> list[dict]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT start_ms, end_ms, text FROM transcript_segments WHERE task_id = ? ORDER BY idx ASC",
            (task_id,),
        ).fetchall()
    return [{"startMs": r["start_ms"], "endMs": r["end_ms"], "text": r["text"]} for r in rows]
