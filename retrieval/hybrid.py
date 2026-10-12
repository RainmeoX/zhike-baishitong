# -*- coding: utf-8 -*-
"""混合检索：关键词路（FTS5+LIKE+同义词）+ 语义路（向量）→ RRF 融合。

语义路未配置（无 embedding key）时自动退化为纯关键词路。
重建向量库：python -m retrieval.hybrid --rebuild
"""
import datetime, json

from api.log import get_logger
from retrieval import vector
from retrieval.rerank import rerank
from retrieval.search import search as keyword_search
from retrieval.db import get_conn

logger = get_logger(__name__)

RRF_K = 60  # RRF 常数

# 制度类长期有效文档关键词：标题命中则不做时效降权（诊断报告修复 2）
EVERGREEN_KEYWORDS = ("办法", "规定", "预案", "制度", "须知", "细则")

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
        except Exception as e:
            logger.warning("语义路失败，关键词路兜底: %s", e)

    fused = sorted(scores.items(), key=lambda x: -x[1])[:topk * 2]  # 候选池留给重排

    results = []
    for did, s in fused:
        d = kw_by_id.get(did) or _doc_by_id(did)
        if d is None:
            continue
        d = dict(d)
        d["score"] = round(s * 1000)
        d["routes"] = "".join(sorted(routes.get(did, [])))  # kw=关键词命中 sem=语义命中
        results.append(d)

    # 重排精排（bge-reranker）：query vs 标题+正文，失败自动保持 RRF 序
    conn = get_conn()
    empty_ids = set()  # 空内容文档 id（图片/表格页，reranker 无法有效评估）
    def _text_of(d):
        row = conn.execute("SELECT content FROM documents WHERE doc_id=?",
                           (str(d["doc_id"]),)).fetchone()
        content = (row["content"] or "") if row else ""
        if content.strip():
            return d["title"] + chr(10) + content[:800]
        # 空内容文档（图片/表格页）：标题加权 + 部门/栏目补充上下文
        empty_ids.add(str(d["doc_id"]))
        dept = d.get("department", "")
        return d["title"] + " " + d["title"] + f" {dept} {d.get('column_name', '')}"
    results = rerank(query, results, _text_of, topk=len(results))  # 不截断，留给融合打分后裁

    # 时效降权：重排相关性 × 年份权重（当年 1.0 / 去年 0.75 / 更早 0.5）
    # 制度类长期有效文档（办法/规定/预案/制度/须知/细则）不做时效降权
    year = datetime.date.today().year
    def _recency(d):
        title = d.get("title", "") or ""
        if any(k in title for k in EVERGREEN_KEYWORDS):
            return 1.0
        try:
            y = int(str(d.get("publish_time", ""))[:4])
        except (ValueError, TypeError):
            return 0.75
        if y >= year: return 1.0
        if y == year - 1: return 0.75
        return 0.5
    # 最终分 = 融合分 × 时效权重
    # 融合 rerank（精排）与 RRF（粗排）；空内容文档 reranker 无法有效评估，提高 RRF 权重
    max_rrf = max((d["score"] for d in results), default=1)
    for d in results:
        rrf_norm = d["score"] / max_rrf if max_rrf > 0 else 0
        rerank_s = d.get("rerank_score", rrf_norm)
        if str(d["doc_id"]) in empty_ids:
            blended = 0.2 * rerank_s + 0.4 * rrf_norm  # 空内容：降权封顶 0.4，防止空页登顶（诊断报告修复 1）
        else:
            blended = 0.65 * rerank_s + 0.35 * rrf_norm
        d["final_score"] = round(blended * _recency(d), 4)
    results.sort(key=lambda d: -d["final_score"])
    conn.close()
    return results[:topk]

def routes_of(result):
    return result.get("routes", "")


if __name__ == "__main__":
    import sys
    if "--rebuild" in sys.argv:
        ok, msg = rebuild_vectors()
        print(f"{'✅' if ok else '⚠️'} {msg}")
    else:
        print("用法: python -m retrieval.hybrid --rebuild")
