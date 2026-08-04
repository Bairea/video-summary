"""settings 表数据访问（key-value JSON）。与旧 TS settingsRepo.ts 行为一致。"""

import json
from datetime import datetime, timezone

from ..db import db_session
from ..types import default_settings

SETTINGS_KEY = "app_settings_v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def load_settings() -> dict:
    with db_session() as conn:
        row = conn.execute("SELECT value_json FROM settings WHERE key = ?", (SETTINGS_KEY,)).fetchone()
    if not row:
        return default_settings()
    try:
        parsed = json.loads(row["value_json"])
        defaults = default_settings()
        return {
            **defaults,
            **parsed,
            "ai": {**defaults["ai"], **parsed.get("ai", {})},
            "download": {**defaults["download"], **parsed.get("download", {})},
            "storage": {**defaults["storage"], **parsed.get("storage", {})},
        }
    except (json.JSONDecodeError, TypeError):
        return default_settings()


def save_settings(partial: dict) -> dict:
    merged = _merge_settings(partial)
    with db_session() as conn:
        conn.execute(
            "INSERT INTO settings (key, value_json, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at",
            (SETTINGS_KEY, json.dumps(merged), _now()),
        )
    return merged


def _merge_settings(partial: dict) -> dict:
    current = load_settings()
    return {
        **current,
        **partial,
        "ai": {**current["ai"], **partial.get("ai", {})},
        "download": {**current["download"], **partial.get("download", {})},
        "storage": {**current["storage"], **partial.get("storage", {})},
    }
