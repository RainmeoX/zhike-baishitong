# -*- coding: utf-8 -*-
"""项目 .env 加载器：把项目根目录 .env 的键值注入 os.environ（不覆盖已有）。

所有依赖 HWMAAS_* / GITCODE_TOKEN 环境变量的模块在读取环境前 import 本模块调用 load()。
"""
import os
from pathlib import Path

_LOADED = False

def load():
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip()
        if k and v and k not in os.environ:
            os.environ[k] = v
