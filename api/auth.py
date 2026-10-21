# -*- coding: utf-8 -*-
"""管理后台鉴权：用户名密码 + HMAC-SHA256 签名 token。

凭据来自 .env（不覆盖已有环境变量）：
  ADMIN_USERNAME  默认 admin
  ADMIN_PASSWORD  默认 zcst-admin（README 提示改掉）
  ADMIN_SECRET    签名密钥，未设置时进程启动随机生成（重启即失效）

纯标准库实现，不新增第三方依赖。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from typing import Optional

from fastapi import Header, HTTPException

from retrieval.maas_env import load

load()

_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
_PASSWORD = os.getenv("ADMIN_PASSWORD", "zcst-admin")
_SECRET = os.getenv("ADMIN_SECRET", "") or secrets.token_hex(32)

_TOKEN_TTL = 12 * 3600  # 12 小时

# PBKDF2 参数
_PBKDF2_ITERATIONS = 100_000


def _hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 加盐哈希，返回 'salt$hexdigest'。"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS
    )
    return f"{salt}${digest.hex()}"


def _verify_hash(password: str, stored: str) -> bool:
    """校验哈希（常量时间比较）。"""
    try:
        salt, hexdigest = stored.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS
    )
    return hmac.compare_digest(digest.hex(), hexdigest)


def _load_password_hash() -> Optional[str]:
    """从 admin_meta 表读密码哈希，无记录返回 None。"""
    from retrieval.db import get_conn, init_db
    conn = get_conn()
    init_db(conn)
    row = conn.execute("SELECT value FROM admin_meta WHERE key='password_hash'").fetchone()
    conn.close()
    return row["value"] if row else None


def verify_password(password: str) -> bool:
    """优先校验持久化哈希；无记录时回退到 .env/默认值。"""
    stored = _load_password_hash()
    if stored:
        return _verify_hash(password, stored)
    return secrets.compare_digest(password, _PASSWORD)


def set_password(new_password: str) -> None:
    """持久化新密码哈希（覆盖旧值）。"""
    from retrieval.db import get_conn, init_db
    conn = get_conn()
    init_db(conn)
    conn.execute(
        "INSERT INTO admin_meta(key, value) VALUES('password_hash', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (_hash_password(new_password),),
    )
    conn.commit()
    conn.close()


def change_password(old_password: str, new_password: str) -> bool:
    """校验旧密码后写入新密码。旧密码错误返回 False。"""
    if not verify_password(old_password):
        return False
    set_password(new_password)
    return True


# 登录限流：IP -> [失败次数, 锁定截止时间戳]
_failures = {}


def _sign(payload_b64: str) -> str:
    return hmac.new(_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def issue_token(username: str) -> str:
    """签发 token：payload = base64url({username, exp})，附签名。"""
    payload = _b64url(('{"username":"%s","exp":%d}' % (username, int(time.time()) + _TOKEN_TTL)).encode())
    return payload + "." + _sign(payload)


def verify_token(token: str) -> Optional[str]:
    """验签 + 查过期。返回用户名，无效返回 None。"""
    if not token or "." not in token:
        return None
    payload_b64, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(_sign(payload_b64), sig):
        return None
    try:
        import json
        data = json.loads(_b64url_decode(payload_b64))
        if int(data["exp"]) < time.time():
            return None
        return data["username"]
    except Exception:
        return None


def authenticate(username: str, password: str) -> bool:
    """校验凭据（常量时间比较），登录限流在此判断。"""
    key = username
    now = time.time()
    if key in _failures:
        fails, lock_until = _failures[key]
        if now < lock_until:
            return False
        if now >= lock_until and fails >= 5:
            _failures.pop(key, None)

    ok = secrets.compare_digest(username, _USERNAME) and verify_password(password)
    if not ok:
        fails, _ = _failures.get(key, (0, 0))
        fails += 1
        lock_until = now + 300 if fails >= 5 else 0
        _failures[key] = (fails, lock_until)
        return False
    _failures.pop(key, None)
    return True


def require_admin(authorization: Optional[str] = Header(default=None)) -> str:
    """FastAPI 依赖：校验 Bearer token，失败抛 401。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    username = verify_token(authorization[len("Bearer "):])
    if not username:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return username
