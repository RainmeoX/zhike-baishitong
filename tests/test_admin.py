# -*- coding: utf-8 -*-
"""管理后台接口与鉴权测试。

运行：python -m pytest tests/test_admin.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.auth import issue_token, verify_token, authenticate, verify_password, set_password
from api.main import app


def _login(client):
    return client.post("/admin/login", json={"username": "admin", "password": "zcst-admin"})


def _auth_header(client):
    r = _login(client)
    assert r.status_code == 200
    return {"Authorization": "Bearer " + r.json()["token"]}


class TestAuth:
    def test_login_ok(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = _login(c)
        assert r.status_code == 200
        assert "token" in r.json()

    def test_login_wrong_password(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.post("/admin/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401

    def test_protected_requires_token(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        assert c.get("/admin/documents").status_code == 401
        assert c.get("/admin/documents", headers={"Authorization": "Bearer bad"}).status_code == 401

    def test_token_roundtrip(self):
        token = issue_token("admin")
        assert verify_token(token) == "admin"

    def test_tampered_token_rejected(self):
        token = issue_token("admin")
        payload, sig = token.rsplit(".", 1)
        assert verify_token(payload + "." + "0" * 64) is None

    def test_expired_token_rejected(self):
        token = issue_token("admin")
        payload, sig = token.rsplit(".", 1)
        import json, base64, time
        data = json.loads(base64.urlsafe_b64decode(payload + "=="))
        data["exp"] = int(time.time()) - 10
        new_payload = base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()
        assert verify_token(new_payload + "." + sig) is None


class TestAdminEndpoints:
    def test_documents_list(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/admin/documents", headers=_auth_header(c))
        assert r.status_code == 200
        d = r.json()
        assert "total" in d and "items" in d
        assert d["total"] > 0

    def test_documents_filter_department(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/admin/documents", params={"department": "教务处"}, headers=_auth_header(c))
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["department"] == "教务处"

    def test_document_detail(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        lst = c.get("/admin/documents", params={"size": 1}, headers=_auth_header(c)).json()
        doc_id = lst["items"][0]["doc_id"]
        r = c.get(f"/admin/documents/{doc_id}", headers=_auth_header(c))
        assert r.status_code == 200
        assert r.json()["doc_id"] == doc_id

    def test_document_not_found(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/admin/documents/not-exist-id", headers=_auth_header(c))
        assert r.status_code == 404

    def test_spotcheck(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.post("/admin/spotcheck", json={"question": "报修电话"}, headers=_auth_header(c))
        assert r.status_code == 200
        assert "results" in r.json()

    def test_spotcheck_empty_question(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.post("/admin/spotcheck", json={"question": "  "}, headers=_auth_header(c))
        assert r.status_code == 400

    def test_overview(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/admin/stats/overview", headers=_auth_header(c))
        assert r.status_code == 200
        d = r.json()
        assert "documents_total" in d and "queries_total" in d

    def test_hot_stats_shape(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/admin/stats/hot", headers=_auth_header(c))
        assert r.status_code == 200
        assert "items" in r.json()


class TestChangePassword:
    def _restore_default(self):
        """恢复默认密码，避免污染其他用例。"""
        from retrieval.db import get_conn
        conn = get_conn()
        conn.execute("DELETE FROM admin_meta WHERE key='password_hash'")
        conn.commit()
        conn.close()

    def test_change_password_success(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        try:
            r = c.post("/admin/change-password",
                       json={"old_password": "zcst-admin", "new_password": "newpass123"},
                       headers=_auth_header(c))
            assert r.status_code == 200
            # 旧密码失效，新密码可登录
            assert c.post("/admin/login", json={"username": "admin", "password": "zcst-admin"}).status_code == 401
            assert c.post("/admin/login", json={"username": "admin", "password": "newpass123"}).status_code == 200
        finally:
            self._restore_default()

    def test_change_password_wrong_old(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        self._restore_default()
        r = c.post("/admin/change-password",
                   json={"old_password": "wrong-old", "new_password": "whatever123"},
                   headers=_auth_header(c))
        assert r.status_code == 400
        # 默认密码仍有效
        assert c.post("/admin/login", json={"username": "admin", "password": "zcst-admin"}).status_code == 200

    def test_change_password_too_short(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        self._restore_default()
        r = c.post("/admin/change-password",
                   json={"old_password": "zcst-admin", "new_password": "123"},
                   headers=_auth_header(c))
        assert r.status_code == 400

    def test_change_password_requires_auth(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        self._restore_default()
        r = c.post("/admin/change-password",
                   json={"old_password": "zcst-admin", "new_password": "newpass123"})
        assert r.status_code == 401
