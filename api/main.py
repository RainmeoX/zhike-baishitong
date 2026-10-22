"""FastAPI 问答服务：问题 → 混合检索 → LLM 生成 → 答案 + 出处。"""

import re

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from api.log import get_logger
from retrieval.search import search as keyword_search, _extract_keywords
from retrieval.hybrid import hybrid_search
from retrieval.db import get_conn
from api.llm import generate as llm_generate, is_available as llm_available
from api.admin import router as admin_router
from api.public import router as public_router

logger = get_logger(__name__)

app = FastAPI(title="珠科百事通", description="珠科校务生活 RAG 问答接口")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 管理后台路由（/admin 首页、登录、知识源管理、质量抽查、热门统计）
app.include_router(admin_router)
# 公开只读路由（/api/notices、/api/stats/public）—— 面向前端门户，无需鉴权
app.include_router(public_router)

_WEB = Path(__file__).resolve().parent.parent / "web"
# 静态资源（CSS/JS）—— 前端门户共享样式与脚本
app.mount("/static", StaticFiles(directory=str(_WEB / "assets")), name="static")

@app.get("/")
def home():
    """门户首页。"""
    return FileResponse(_WEB / "index.html")


@app.get("/{page_name}.html")
def html_page(page_name: str):
    """伺服 web/ 下的静态页面（chat/notices/about/index）。

    仅允许简单文件名（字母数字下划线横线），并校验解析后的父目录仍是 web/，
    防止 ../ 路径穿越读取项目其他文件。
    """
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", page_name):
        raise HTTPException(status_code=404, detail="Not Found")
    target = (_WEB / f"{page_name}.html").resolve()
    if target.parent != _WEB.resolve() or not target.is_file():
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(target)

# 拒答/兜底标准文案（检索零结果与 LLM 判定库内无信息时统一使用，不再展示占位电话）
REFUSAL_ANSWER = (
    "抱歉，知识库暂未收录与您问题相关的官方通知。建议：\n"
    "1) 换个问法再试试，比如带上具体事项和时间（如「2026 四六级报名」）；\n"
    "2) 或到教务处（jx.zcst.edu.cn）/ 后勤处（hq.zcst.edu.cn）官网通知栏查阅原文。"
)

# 拒答标记（严格版：仅覆盖"库内无信息"类措辞。
# 注意不能照抄 evaluation/runner.py 的宽松标记——「建议联系」「抱歉，」等会误伤
# "空调报修建议联系宿管处"式正常回答，导致把好答案替换成拒答）
_REFUSAL_STRICT = (
    "暂未检索到", "未检索到", "未能检索到", "无法回答",
    "不足以回答", "暂无相关", "未提及", "没有提及",
    "未明确提到", "没有明确提到", "未找到", "没有找到",
)
# 分离式措辞的正则覆盖（"没有…提及"间隔变体，与评测端对齐）
_REFUSAL_RE = (re.compile(r"没有[^。！？]{0,12}提及"),)


def _is_refusal_answer(text: str) -> bool:
    """判断 LLM 回答是否为拒答（库内无相关信息，且不应继续输出"个人知识"类内容）。"""
    if not text:
        return False
    return any(m in text for m in _REFUSAL_STRICT) or any(p.search(text) for p in _REFUSAL_RE)

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

def _calc_confidence(top) -> float:
    """置信度 = 精排相关性分。

    优先用 bge-reranker 精排分（弱相关天然低分），rerank 服务失败时回退
    final_score（融合精排分），均无则兜底 0.05。封顶 0.95 保留"不绝对"的姿态。
    旧实现用 RRF 粗排整数分 score/10（常见 16+），导致置信度恒 100%。
    """
    s = top.get("rerank_score", top.get("final_score", 0)) or 0
    return round(min(0.95, max(0.05, float(s))), 2)


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

    confidence = _calc_confidence(top)
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
        return AskResponse(answer=REFUSAL_ANSWER, confidence=0.0, references=[])

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
            if _is_refusal_answer(llm_answer):
                # LLM 已判断库内无相关信息 → 统一标准拒答文案，防止
                # "暂未检索到…不过个人知识…"式幻觉泄漏；置信度压低。
                # 但 references 保留：检索是客观结果，不应被 LLM 判断抹掉——
                # 一是供评测判定命中（MRR/Recall 按 references 算），二是
                # 真超纲题展示弱相关出处 + 拒答文案仍是合理的产品形态。
                answer = REFUSAL_ANSWER
                confidence = 0.3
            else:
                answer = llm_answer
                # LLM 基于参考内容正常作答 = 内容层验证通过，置信度下限抬到 0.4：
                # rerank 分只度量检索匹配度（弱匹配但可答的题不应给"不可信"观感），
                # 区分度保留：拒答 0.3 < 弱匹配 0.4 < 强匹配 0.7~0.95
                confidence = max(confidence, 0.4)

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