"""关键词检索：FTS5 精确命中数字/英文 + LIKE 中文子串 + 同义词扩展。"""

import re

from retrieval.db import get_conn, init_db

SYNONYMS = {
    "校巴": ["班车", "巴士", "校车", "校园巴士"],
    "校车": ["班车", "巴士", "校园巴士"],
    "班车": ["校巴", "校车", "巴士"],
    "饭堂": ["食堂", "餐厅"],
    "食堂": ["饭堂", "餐厅"],
    "宿舍": ["公寓", "住宿"],
    "公寓": ["宿舍", "住宿"],
    "缴费": ["收费", "交费", "水费", "电费"],
    "收费": ["缴费", "交费"],
    "报修": ["维修", "保修", "故障"],
    "维修": ["报修", "保修"],
    "转专业": ["转系", "专业调整"],
    "分数线": ["录取线", "录取分数", "投档线"],
    "录取": ["分数线", "录取分"],
    "奖学金": ["助学金", "奖助"],
    "助学金": ["奖学金", "奖助"],
    "四六级": ["四、六级", "四级", "六级", "CET"],
    "四级": ["四、六级", "CET"],
    "六级": ["四、六级", "CET"],
    "重修": ["补考"],
    "学费": ["缴费", "收费"],
}


def _extract_keywords(query):
    keywords = set()
    for kw, syns in SYNONYMS.items():
        if kw.lower() in query.lower():
            keywords.add(kw)
            keywords.update(syns)
    # 滑动窗口提取 2-4 字中文子串（避免长查询被当一个 token）
    for i in range(len(query)):
        for n in (2, 3, 4):
            if i + n <= len(query):
                sub = query[i:i+n]
                if re.match(r"[\u4e00-\u9fff]+$", sub):
                    keywords.add(sub)
    return keywords


def search(query, topk=10, db_path=None, conn=None):
    own = conn is None
    conn = conn or get_conn(db_path)
    init_db(conn)
    cur = conn.cursor()

    scored = {}

    tokens = [t for t in re.findall(r"[0-9A-Za-z]+", query) if len(t) >= 2]
    if tokens:
        fts_query = " OR ".join(f'"{t}"' for t in tokens)
        try:
            rows = cur.execute(
                "SELECT doc_id, bm25(documents_fts) AS r FROM documents_fts"
                " WHERE documents_fts MATCH ? ORDER BY r LIMIT ?",
                (fts_query, topk * 3),
            ).fetchall()
            for row in rows:
                scored[row["doc_id"]] = scored.get(row["doc_id"], 0) + 10
        except Exception:
            pass

    for kw in _extract_keywords(query):
        like = f"%{kw}%"
        rows = cur.execute(
            "SELECT doc_id, title, content FROM documents"
            " WHERE title LIKE ? OR content LIKE ? LIMIT 60",
            (like, like),
        ).fetchall()
        for row in rows:
            base = 0
            in_title = kw in row["title"]
            in_content = kw in (row["content"] or "")
            if in_title:
                base += 6
            if in_content:
                base += 1
            if in_title and not (row["content"] or "").strip():
                base += 4
            if base:
                scored[row["doc_id"]] = scored.get(row["doc_id"], 0) + base

    results = []
    for doc_id, score in sorted(scored.items(), key=lambda x: -x[1])[:topk]:
        row = cur.execute(
            "SELECT * FROM documents WHERE doc_id=?", (doc_id,)
        ).fetchone()
        if row:
            results.append({
                "doc_id": row["doc_id"],
                "title": row["title"],
                "department": row["department"],
                "column_name": row["column_name"],
                "source_url": row["source_url"],
                "publish_time": row["publish_time"],
                "score": score,
            })
    if own:
        conn.close()
    return results