"""将 data/clean/*.jsonl 导入 SQLite 并建立 FTS5 索引。"""

import json

from crawler.config import CLEAN_DIR
from crawler.cleaner import clean_text
from retrieval.db import get_conn, init_db, DB_PATH


def build_index(clean_dir=None):
    clean_dir = clean_dir or CLEAN_DIR
    conn = get_conn()
    init_db(conn)
    cur = conn.cursor()

    existing = {r[0] for r in cur.execute("SELECT doc_id FROM documents")}
    inserted = 0

    for jsonl in sorted(clean_dir.glob("*.jsonl")):
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            doc_id = rec.get("id") or rec["source_url"]
            if doc_id in existing:
                continue
            title = clean_text(rec.get("title", ""))
            content = clean_text(rec.get("content", ""))
            dept = rec.get("department", "")
            column = rec.get("column", "")
            url = rec.get("source_url", "")
            publish = rec.get("publish_time", "")

            cur.execute(
                "INSERT INTO documents(doc_id, title, content, publish_time, department, column_name, source_url)"
                " VALUES(?,?,?,?,?,?,?)",
                (doc_id, title, content, publish, dept, column, url),
            )
            rid = cur.lastrowid
            cur.execute(
                "INSERT INTO documents_fts(rowid, title, content, department, column_name, doc_id, source_url, publish_time)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (rid, title, content, dept, column, doc_id, url, publish),
            )
            existing.add(doc_id)
            inserted += 1

    conn.commit()
    conn.close()
    return inserted