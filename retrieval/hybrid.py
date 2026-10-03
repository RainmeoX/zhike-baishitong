# -*- coding: utf-8 -*-
"""混合检索：关键词路（FTS5+LIKE+同义词）+ 语义路（向量）→ RRF 融合。

语义路未配置（无 embedding key）时自动退化为纯关键词路。
重建向量库：python -m retrieval.hybrid --rebuild
"""
import json

from retrieval import vector
from retrieval.search import search as keyword_search
from retrieval.db import get_conn

RRF_K = 60  # RRF 常数

def rebuild_vectors():
    """从 documents 表全量重建向量库。返回 (ok, message)。"""
    conn = get_conn()
    rows = conn.execute("SELECT doc_id, title, content FROM documents").fetchall()
    conn.close()
    docs = [{"id": r["doc_id"], "title": r["title"], "content": r["content"]} for r in rows]
    return vector.rebuild(docs)

def _doc_by_id(doc_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT doc_id, title, department, column_name, source_url, publish_time"
        " FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

def hybrid_search(query, topk=5):
    """RRF 融合两路检索。返回与 keyword_search 同构的文档列表（附 routes 字段）。"""
    kw = keyword_search(query, topk=topk)
    kw_by_id = {str(d["doc_id"]): d for d in kw}

    scores, routes = {}, {}
    for rank, d in enumerate(kw):
        did = str(d["doc_id"])
        scores[did] = scores.get(did, 0) + 1.0 / (RRF_K + rank + 1)
        routes.setdefault(did, set()).add("kw")

    if vector.available():
        try:
            for rank, (did, _) in enumerate(vector.semantic_search(query, topk=topk)):
                scores[did] = scores.get(did, 0) + 1.0 / (RRF_K + rank + 1)
                routes.setdefault(did, set()).add("sem")
        except Exception:
            pass  # 语义路失败 → 关键词路兜底

    results = []
    for did, s in sorted(scores.items(), key=lambda x: -x[1])[:topk]:
        d = kw_by_id.get(did) or _doc_by_id(did)
        if d is None:
            continue
        d = dict(d)
        d["score"] = round(s * 1000)
        d["routes"] = "".join(sorted(routes.get(did, [])))  # kw=关键词命中 sem=语义命中
        results.append(d)
    return results

def routes_of(result):
    return result.get("routes", "")
