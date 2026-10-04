"""FastAPI 问答服务：问题 → 混合检索 → 生成（占位）→ 答案 + 出处。"""

import re

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from retrieval.search import search as keyword_search, _extract_keywords
from retrieval.hybrid import hybrid_search
from retrieval.db import get_conn
from api.llm import generate as llm_generate, is_available as llm_available

app = FastAPI(title="珠科百事通", description="珠科校务生活 RAG 问答接口")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
    question: str
    topk: int = 5

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
    answer += "\n\n（当前为检索抽取式回答，大模型生成能力待接入华为云 MaaS）"

    confidence = min(1.0, top["score"] / 10.0)
    return answer, confidence

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    try:
        results = hybrid_search(req.question, topk=req.topk)  # 语义路可用则混合，否则自动退化
    except Exception:
        results = keyword_search(req.question, topk=req.topk)
    if not results:
        return AskResponse(answer=FALLBACK_ANSWER, confidence=0.0, references=[])

    answer, confidence = _build_answer(results[0], results, req.question)

    if llm_available():
        conn = get_conn()
        row = conn.execute(
            "SELECT content FROM documents WHERE doc_id=?", (results[0]["doc_id"],)
        ).fetchone()
        conn.close()
        context = results[0]["title"] + "\n" + (row["content"] or "" if row else "")
        llm_answer = llm_generate(req.question, context)
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
    return AskResponse(answer=answer, confidence=confidence, references=references)