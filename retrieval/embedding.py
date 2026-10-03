# -*- coding: utf-8 -*-
"""语义路：华为云 MaaS embedding 客户端（OpenAI 兼容 /embeddings 接口）。

未配置 HWMAAS_API_KEY 时 available() 返回 False，混合检索自动退化为纯关键词路。
"""
import os, json, urllib.request

from retrieval.maas_env import load
load()

_API_KEY = os.getenv("HWMAAS_API_KEY", "")
# MaaS embedding 接入点与模型名：在 MaaS 控制台"调用说明"里复制，或由 ZY 填入 .env
_ENDPOINT = os.getenv("HWMAAS_EMBED_ENDPOINT", "")   # 例：https://api.modelarts-maas.com/v1/embeddings
_MODEL = os.getenv("HWMAAS_EMBED_MODEL", "")          # 例：pangu-embedding-v1 / bge-m3

def available():
    return bool(_API_KEY and _ENDPOINT and _MODEL)

def embed(texts):
    """批量向量化。texts: list[str] → list[list[float]]；失败抛异常由调用方兜底。"""
    if not available():
        raise RuntimeError("embedding 未配置")
    body = json.dumps({"model": _MODEL, "input": texts}).encode()
    req = urllib.request.Request(_ENDPOINT, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {_API_KEY}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    # OpenAI 兼容格式：{"data": [{"embedding": [...]}, ...]}
    items = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
    return [d["embedding"] for d in items]

def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0
