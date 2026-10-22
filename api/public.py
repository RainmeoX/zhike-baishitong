# -*- coding: utf-8 -*-
"""公开只读接口：通知速览 / 部门统计。

与 /admin/* 不同，本路由无需鉴权，面向前端门户开放。
- 列表接口不返回正文 content（减少传输、避免列表页超长）；
- 统计接口为脱敏版，不暴露 queries_total（只给今日问答量作热度展示）。
"""

from fastapi import APIRouter, HTTPException

from retrieval.db import get_conn

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/notices")
def list_notices(
    page: int = 1,
    size: int = 20,
    department: str = "",
    column: str = "",
    q: str = "",
):
    """通知分页列表：关键词 + 部门 + 栏目过滤，按发布时间倒序，不含正文。"""
    page = max(1, page)
    size = min(max(1, size), 100)
    conn = get_conn()

    where, args = [], []
    if q:
        where.append("(title LIKE ? OR content LIKE ?)")
        args += [f"%{q}%", f"%{q}%"]
    if department:
        where.append("department = ?")
        args.append(department)
    if column:
        where.append("column_name = ?")
        args.append(column)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    total = conn.execute(
        f"SELECT COUNT(*) FROM documents {where_sql}", args
    ).fetchone()[0]
    rows = conn.execute(
        f"SELECT doc_id, title, department, column_name, source_url, publish_time "
        f"FROM documents {where_sql} ORDER BY publish_time DESC LIMIT ? OFFSET ?",
        args + [size, (page - 1) * size],
    ).fetchall()
    conn.close()

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [dict(r) for r in rows],
    }


@router.get("/notices/{doc_id}")
def get_notice(doc_id: str):
    """通知详情：返回完整字段（含正文 content）。"""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM documents WHERE doc_id=?", (doc_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="文档不存在")
    return dict(row)


@router.get("/stats/public")
def public_stats():
    """脱敏版概览：文档总数 / 部门分布 / 今日问答量（不暴露累计问答量）。"""
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    dept_rows = conn.execute(
        "SELECT department, COUNT(*) AS cnt FROM documents GROUP BY department"
    ).fetchall()
    today_q = conn.execute(
        "SELECT COUNT(*) FROM query_log WHERE date(created_at)=date('now','localtime')"
    ).fetchone()[0]
    conn.close()
    return {
        "documents_total": total,
        "departments": [dict(r) for r in dept_rows],
        "queries_today": today_q,
    }


@router.get("/stats/hot")
def hot_questions(limit: int = 6):
    """热门问题（大家都在问）：来自 query_log 埋点聚合，无需鉴权。

    面向前端门户展示实时热点，仅返回问句与次数，不含用户信息。
    """
    limit = min(max(1, limit), 20)
    conn = get_conn()
    rows = conn.execute(
        "SELECT question, COUNT(*) AS cnt FROM query_log "
        "GROUP BY question ORDER BY cnt DESC, MAX(created_at) DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return {"items": [dict(r) for r in rows]}
