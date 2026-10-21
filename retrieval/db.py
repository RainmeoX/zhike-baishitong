"""检索层数据库连接与建表。"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "zcst.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT UNIQUE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    publish_time TEXT,
    department TEXT,
    column_name TEXT,
    source_url TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    title, content, department, column_name,
    doc_id UNINDEXED, source_url UNINDEXED, publish_time UNINDEXED
);

CREATE TABLE IF NOT EXISTS query_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    hit_doc_id TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS admin_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_conn(db_path=None):
    conn = sqlite3.connect(str(db_path or DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.executescript(SCHEMA)
    conn.commit()