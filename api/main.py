"""FastAPI 问答服务：问题 → 混合检索 → LLM 生成 → 答案 + 出处。"""

import re

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from api.log import get_logger
from retrieval.search import search as keyword_search, _extract_keywords
from retrieval.hybrid import hybrid_search
from retrieval.db import get_conn
from api.llm import generate as llm_generate, is_available as llm_available
from api.admin import router as admin_router

logger = get_logger(__name__)

app = FastAPI(title="珠科百事通", description="珠科校务生活 RAG 问答接口")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 管理后台路由（/admin 首页、登录、知识源管理、质量抽查、热门统计）
app.include_router(admin_router)

_WEB = Path(__file__).resolve().parent.parent / "web"

@app.get("/")
def home():
    """网页测试台（也用作文档入口）。"""
    return FileResponse(_WEB / "index.html")

FALLBACK_ANSWER = (
    "抱歉，当前知识库暂未检索到与您问题相关的官方信息。"
    "建议联系对应部门获取最新答复：\n"
    "教务处：0756-7626XXX（待核实）；后勤处：0756-7626267；招生办：0756-7626XXX（待核实）。"
)

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500, description="学生问题（1-500 字）")
    topk: int = Field(default=5, ge=1, le=20, description="返回条数（1-20）")

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v):
        if not v.strip():
            raise ValueError("问题不能为空白")
        return v.strip()

class Reference(BaseModel):
    title: str
    department: str
    column: str
    source_url: str
    score: int

class AskResponse(BaseModel):
    answer: str
    confidence: float
    references: list[Reference]

class ErrorResponse(BaseModel):
    error: str
    detail: str = ""

def _extract_snippet(content, query, max_len=300):
    if not content or not content.strip():
        return ""
    sentences = re.split(r"[。；！？\n]+", content)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return content[:max_len]
    kws = _extract_keywords(query)
    best_idx, best_score = 0, -1
    for i, s in enumerate(sentences):
        sc = sum(1 for kw in kws if kw in s)
        if sc > best_score:
            best_score, best_idx = sc, i
    result = sentences[best_idx]
    cur_len = len(result)
    j = best_idx + 1
    while j < len(sentences) and cur_len + len(sentences[j]) + 1 <= max_len:
        result += "。" + sentences[j]
        cur_len += len(sentences[j]) + 1
        j += 1
    j = best_idx - 1
    while j >= 0 and cur_len + len(sentences[j]) + 1 <= max_len:
        result = sentences[j] + "。" + result
        cur_len += len(sentences[j]) + 1
        j -= 1
    return result

def _build_answer(top, results, query) -> tuple[str, float]:
    conn = get_conn()
    row = conn.execute(
        "SELECT content FROM documents WHERE doc_id=?", (top["doc_id"],)
    ).fetchone()
    conn.close()

    snippet = _extract_snippet(row["content"] if row else None, query)
    if not snippet:
        snippet = "（该通知正文为图片或动态加载，请查看原文获取详细内容）"

    answer = f"根据「{top['title']}」：{snippet}"
    if len(results) > 1:
        answer += f"\n\n（另有 {len(results) - 1} 条相关依据，详见出处列表）"
    answer += "\n\n（当前为检索抽取式回答，大模型生成未启用时以此兜底）"

    confidence = min(1.0, top["score"] / 10.0)
    return answer, confidence

@app.get("/health")
def health():
    return {"status": "ok"}

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """全局异常兜底：未预期的错误返回结构化 500，不泄露堆栈。"""
    logger.error("未处理异常: %s %s -> %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": "服务内部错误，请稍后重试"},
    )

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    try:
        results = hybrid_search(req.question, topk=req.topk)  # 语义路可用则混合，否则自动退化
    except Exception as e:
        logger.warning("hybrid_search 失败，降级关键词路: %s", e)
        try:
            results = keyword_search(req.question, topk=req.topk)
        except Exception as e2:
            logger.error("关键词路也失败: %s", e2)
            raise HTTPException(status_code=503, detail="检索服务暂时不可用")
    if not results:
        return AskResponse(answer=FALLBACK_ANSWER, confidence=0.0, references=[])

    answer, confidence = _build_answer(results[0], results, req.question)

    if llm_available():
        # 传 top-k 多篇给 LLM，而非仅 top-1
        conn = get_conn()
        refs_for_llm = []
        for r in results:
            row = conn.execute(
                "SELECT content FROM documents WHERE doc_id=?", (r["doc_id"],)
            ).fetchone()
            refs_for_llm.append({
                "title": r["title"],
                "department": r.get("department", ""),
                "content": (row["content"] or "") if row else "",
            })
        conn.close()
        llm_answer = llm_generate(req.question, refs_for_llm)
        if llm_answer:
            answer = llm_answer

    references = [
        Reference(
            title=r["title"],
            department=r["department"],
            column=r["column_name"],
            source_url=r["source_url"],
            score=r["score"],
        )
        for r in results
    ]

    # 埋点：记录问句与命中首条文档，供管理后台热门统计使用（失败不影响回答）
    try:
        from datetime import datetime
        conn = get_conn()
        conn.execute(
            "INSERT INTO query_log(question, hit_doc_id, created_at) VALUES(?,?,?)",
            (req.question, results[0]["doc_id"], datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("query_log 埋点写入失败（不影响回答）: %s", e)

    return AskResponse(answer=answer, confidence=confidence, references=references)