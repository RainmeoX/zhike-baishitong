# -*- coding: utf-8 -*-
"""重排器：bge-reranker-v2-m3（MaaS /rerank），RRF 融合后做精细排序。"""
import json, os, urllib.request

from retrieval.maas_env import load
load()

_API_KEY = os.getenv("HWMAAS_API_KEY", "")
_ENDPOINT = os.getenv("HWMAAS_RERANK_ENDPOINT", "https://api.modelarts-maas.com/v1/rerank")
_MODEL = os.getenv("HWMAAS_RERANK_MODEL", "bge-reranker-v2-m3")

def available():
    return bool(_API_KEY)

def rerank(query, docs, text_of, topk=None):
    """按相关性重排 docs。text_of(doc) 返回参与排序的文本。
    失败时原序返回（RRF 序兜底）。返回的每项附 rerank_score。"""
    if not available() or len(docs) <= 1:
        return docs
    try:
        body = json.dumps({
            "model": _MODEL, "query": query,
            "documents": [text_of(d) for d in docs],
        }).encode()
        req = urllib.request.Request(_ENDPOINT, data=body, method="POST")
        req.add_header("Authorization", f"Bearer {_API_KEY}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as r:
            results = json.loads(r.read().decode()).get("results", [])
        ordered = []
        for item in sorted(results, key=lambda x: -x.get("relevance_score", 0)):
            d = dict(docs[item["index"]])
            d["rerank_score"] = round(item.get("relevance_score", 0), 4)
            ordered.append(d)
        return ordered[:topk] if topk else ordered
    except Exception:
        return docs[:topk] if topk else docs
