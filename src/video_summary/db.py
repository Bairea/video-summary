"""SQLite 连接与表结构。每次操作使用独立连接（WAL 模式），规模下足够安全。"""

import sqlite3
from contextlib import contextmanager

from .paths import resolve_data_dir, resolve_db_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  platform TEXT NOT NULL,
  title TEXT,
  duration_sec INTEGER,
  stage TEXT NOT NULL,
  progress INTEGER,
  error TEXT,
  pipeline_json TEXT,
  language TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transcript_segments (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  start_ms INTEGER NOT NULL,
  end_ms INTEGER NOT NULL,
  text TEXT NOT NULL,
  idx INTEGER NOT NULL,
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS summaries (
  task_id TEXT PRIMARY KEY,
  markdown TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS mindmaps (
  task_id TEXT PRIMARY KEY,
  mermaid TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS qa_messages (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    resolve_data_dir().mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(resolve_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    ensure_column(conn, "tasks", "request_json", "TEXT")
    ensure_column(conn, "tasks", "runtime_json", "TEXT")
    ensure_column(conn, "qa_messages", "metadata_json", "TEXT")


def ensure_column(conn: sqlite3.Connection, table: str, column: str, type_sql: str) -> None:
    cols = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type_sql}")


@contextmanager
def db_session():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
