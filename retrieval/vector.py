# -*- coding: utf-8 -*-
"""语义向量库：SQLite 存 embedding BLOB + 余弦暴力检索。

199 篇文档规模下暴力余弦即可（<10ms），无需 FAISS。
"""
import json, sqlite3, os

from retrieval.embedding import embed, available, cosine

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "vectors.db")

def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS vectors(
        doc_id TEXT PRIMARY KEY,
        model TEXT,
        embedding BLOB)""")
    return c

def rebuild(docs, progress=None):
    """全量重建向量库。docs: list[dict]，需含 id/content 字段。
    语义路未配置时返回 (False, 'embedding 未配置')。"""
    if not available():
        return False, "embedding 未配置"
    c = _conn()
    c.execute("DELETE FROM vectors")
    texts = [(d.get("title", "") + "\n" + d.get("content", ""))[:1500] for d in docs]
    B = 16  # 批量大小，避免超长请求
    vectors = []
    for i in range(0, len(texts), B):
        vectors.extend(embed(texts[i:i + B]))
        if progress:
            progress(min(i + B, len(texts)), len(texts))
    for d, v in zip(docs, vectors):
        c.execute("INSERT OR REPLACE INTO vectors VALUES (?,?,?)",
                  (str(d.get("id")), os.getenv("HWMAAS_EMBED_MODEL", ""), json.dumps(v)))
    c.commit(); c.close()
    return True, f"{len(vectors)} 条向量已入库"

def semantic_search(query, topk=5):
    """语义检索：返回 [(doc_id, score)]，未配置/空库返回 []。"""
    if not available():
        return []
    c = _conn()
    row = c.execute("SELECT COUNT(*) FROM vectors").fetchone()
    if not row or row[0] == 0:
        c.close(); return []
    qv = embed([query])[0]
    model = os.getenv("HWMAAS_EMBED_MODEL", "")
    rows = c.execute("SELECT doc_id, embedding FROM vectors WHERE model=?", (model,)).fetchall()
    c.close()
    scored = []
    for doc_id, blob in rows:
        v = json.loads(blob)
        scored.append((doc_id, cosine(qv, v)))
    scored.sort(key=lambda x: -x[1])
    return scored[:topk]
