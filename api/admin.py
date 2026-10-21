# -*- coding: utf-8 -*-
"""管理后台接口：知识源管理 / 质量抽查 / 热门统计。

全部接口（除 /admin/login 与 /admin 首页）要求 Bearer token，见 api/auth.py。
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.auth import authenticate, issue_token, require_admin, change_password
from retrieval.db import get_conn
from retrieval.hybrid import hybrid_search

router = APIRouter(prefix="/admin", tags=["admin"])

_WEB = Path(__file__).resolve().parent.parent / "web"


class LoginRequest(BaseModel):
    username: str
    password: str


class SpotcheckRequest(BaseModel):
    question: str
    topk: int = 10


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.get("")
def admin_home():
    """管理后台网页入口。"""
    return FileResponse(_WEB / "admin.html")


@router.post("/login")
def login(req: LoginRequest):
    if not authenticate(req.username, req.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"token": issue_token(req.username), "username": req.username}


@router.post("/change-password")
def change_password_endpoint(req: ChangePasswordRequest, _: str = Depends(require_admin)):
    """修改管理员密码（需登录 + 旧密码正确）。"""
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    if not change_password(req.old_password, req.new_password):
        raise HTTPException(status_code=400, detail="旧密码错误")
    return {"ok": True}


@router.get("/documents")
def list_documents(
    page: int = 1,
    size: int = 20,
    q: str = "",
    department: str = "",
    column: str = "",
    _: str = Depends(require_admin),
):
    """知识源分页列表：关键词 + 部门 + 栏目过滤。"""
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

    total = conn.execute(f"SELECT COUNT(*) FROM documents {where_sql}", args).fetchone()[0]
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


@router.get("/documents/{doc_id}")
def get_document(doc_id: str, _: str = Depends(require_admin)):
    conn = get_conn()
    row = conn.execute("SELECT * FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="文档不存在")
    return dict(row)


@router.post("/spotcheck")
def spotcheck(req: SpotcheckRequest, _: str = Depends(require_admin)):
    """质量抽查：输入问题，返回混合检索命中列表（含 routes/score）。"""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    try:
        results = hybrid_search(req.question.strip(), topk=req.topk)
    except Exception:
        results = []
    return {"question": req.question, "results": results}


@router.get("/stats/hot")
def hot_stats(limit: int = 20, _: str = Depends(require_admin)):
    limit = min(max(1, limit), 100)
    conn = get_conn()
    rows = conn.execute(
        "SELECT question, COUNT(*) AS cnt, MAX(created_at) AS last_at "
        "FROM query_log GROUP BY question ORDER BY cnt DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return {"items": [dict(r) for r in rows]}


@router.get("/stats/overview")
def overview(_: str = Depends(require_admin)):
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    dept_rows = conn.execute(
        "SELECT department, COUNT(*) AS cnt FROM documents GROUP BY department"
    ).fetchall()
    today_q = conn.execute(
        "SELECT COUNT(*) FROM query_log WHERE date(created_at)=date('now','localtime')"
    ).fetchone()[0]
    total_q = conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]
    conn.close()
    return {
        "documents_total": total,
        "departments": [dict(r) for r in dept_rows],
        "queries_today": today_q,
        "queries_total": total_q,
    }
