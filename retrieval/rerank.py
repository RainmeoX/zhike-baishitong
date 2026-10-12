# -*- coding: utf-8 -*-
"""重排器：RRF 融合后做精细排序。

主路：硅基流动 SiliconFlow（BAAI/bge-reranker-v2-m3，国内免费）
备路：Jina AI（jina-reranker-v2-base-multilingual，海外，主路失败时自动 fallback）
两路都失败时原序返回（RRF 序兜底）。返回的每项附 rerank_score。
"""
import json, os, urllib.request

from retrieval.maas_env import load
load()

# 主路：硅基流动（HWMAAS_* 变量名沿用，实际指向硅基流动）
_API_KEY = os.getenv("HWMAAS_API_KEY", "")
_ENDPOINT = os.getenv("HWMAAS_RERANK_ENDPOINT", "")
_MODEL = os.getenv("HWMAAS_RERANK_MODEL", "")

# 备路：Jina AI
_FB_KEY = os.getenv("JINA_API_KEY", "")
_FB_ENDPOINT = os.getenv("JINA_RERANK_ENDPOINT", "")
_FB_MODEL = os.getenv("JINA_RERANK_MODEL", "")
_FB_PROXY = os.getenv("JINA_PROXY", "")  # 海外需走本地代理

def available():
    """主路或备路任一可用即返回 True。"""
    return bool(_API_KEY and _ENDPOINT and _MODEL) or bool(_FB_KEY and _FB_ENDPOINT and _FB_MODEL)

def _rerank_call(endpoint, model, api_key, query, docs, text_of, topk, proxy=""):
    """单次重排调用（Cohere 兼容格式）。失败抛异常由上层兜底。"""
    body = json.dumps({
        "model": model, "query": query,
        "documents": [text_of(d) for d in docs],
    }).encode()
    req = urllib.request.Request(endpoint, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    # 有代理时走代理（Jina 海外），无代理直连（硅基流动国内）
    if proxy:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"https": proxy, "http": proxy}))
    else:
        opener = urllib.request.build_opener()
    with opener.open(req, timeout=30) as r:
        results = json.loads(r.read().decode()).get("results", [])
    ordered = []
    for item in sorted(results, key=lambda x: -x.get("relevance_score", 0)):
        d = dict(docs[item["index"]])
        d["rerank_score"] = round(item.get("relevance_score", 0), 4)
        ordered.append(d)
    return ordered[:topk] if topk else ordered

def rerank(query, docs, text_of, topk=None):
    """按相关性重排 docs。text_of(doc) 返回参与排序的文本。
    先试主路（硅基流动），失败自动切备路（Jina）；两路都失败原序返回。"""
    if not available() or len(docs) <= 1:
        return docs[:topk] if topk else docs
    # 主路
    if _API_KEY and _ENDPOINT and _MODEL:
        try:
            return _rerank_call(_ENDPOINT, _MODEL, _API_KEY, query, docs, text_of, topk)
        except Exception:
            pass  # 降级到备路
    # 备路
    if _FB_KEY and _FB_ENDPOINT and _FB_MODEL:
        try:
            return _rerank_call(_FB_ENDPOINT, _FB_MODEL, _FB_KEY, query, docs, text_of, topk, proxy=_FB_PROXY)
        except Exception:
            pass  # 两路都失败
    return docs[:topk] if topk else docs
