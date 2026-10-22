# -*- coding: utf-8 -*-
"""语义路：embedding 客户端（OpenAI 兼容 /embeddings 接口）。

主路：硅基流动 SiliconFlow（BAAI/bge-m3，国内免费）
备路：Jina AI（jina-embeddings-v3，海外，主路失败时自动 fallback）
未配置任何一路时 available() 返回 False，混合检索自动退化为纯关键词路。
"""
import os, json, urllib.request

from api.log import get_logger
from retrieval.maas_env import load
load()

logger = get_logger(__name__)

# 主路：硅基流动（HWMAAS_* 变量名沿用，实际指向硅基流动）
_API_KEY = os.getenv("HWMAAS_API_KEY", "")
_ENDPOINT = os.getenv("HWMAAS_EMBED_ENDPOINT", "")
_MODEL = os.getenv("HWMAAS_EMBED_MODEL", "")

# 备路：Jina AI
_FB_KEY = os.getenv("JINA_API_KEY", "")
_FB_ENDPOINT = os.getenv("JINA_EMBED_ENDPOINT", "")
_FB_MODEL = os.getenv("JINA_EMBED_MODEL", "")
_FB_PROXY = os.getenv("JINA_PROXY", "")  # 海外需走本地代理

def available():
    """主路或备路任一可用即返回 True。"""
    return bool(_API_KEY and _ENDPOINT and _MODEL) or bool(_FB_KEY and _FB_ENDPOINT and _FB_MODEL)

def _embed_call(endpoint, model, api_key, texts, proxy=""):
    """单次向量化调用（OpenAI 兼容格式）。失败抛异常由上层兜底。"""
    body = json.dumps({"model": model, "input": texts}).encode()
    req = urllib.request.Request(endpoint, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    # 有代理时走代理（Jina 海外），无代理直连（硅基流动国内）
    if proxy:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"https": proxy, "http": proxy}))
    else:
        opener = urllib.request.build_opener()
    with opener.open(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    # OpenAI 兼容格式：{"data": [{"embedding": [...]}, ...]}
    items = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
    return [d["embedding"] for d in items]

def embed(texts):
    """批量向量化。texts: list[str] → list[list[float]]。
    先试主路（硅基流动），失败自动切备路（Jina）；两路都失败抛异常由调用方兜底。"""
    if not available():
        raise RuntimeError("embedding 未配置")
    # 主路
    if _API_KEY and _ENDPOINT and _MODEL:
        try:
            return _embed_call(_ENDPOINT, _MODEL, _API_KEY, texts)
        except Exception as e:
            logger.warning("embedding 主路失败，降级备路: %s", e)
    # 备路
    if _FB_KEY and _FB_ENDPOINT and _FB_MODEL:
        return _embed_call(_FB_ENDPOINT, _FB_MODEL, _FB_KEY, texts, proxy=_FB_PROXY)
    raise RuntimeError("embedding 主备路均不可用")

def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0
