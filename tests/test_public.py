# -*- coding: utf-8 -*-
"""公开只读接口测试（/api/notices、/api/stats/public）。

运行：python -m pytest tests/test_public.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app


class TestPublicNotices:
    def test_notices_list_ok(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/api/notices")
        assert r.status_code == 200
        d = r.json()
        assert "total" in d and "page" in d and "size" in d and "items" in d
        assert d["total"] > 0
        # 列表项不应包含 content 字段（减少传输）
        if d["items"]:
            assert "content" not in d["items"][0]

    def test_notices_list_structure(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/api/notices", params={"size": 3})
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) <= 3
        for it in items:
            assert "doc_id" in it
            assert "title" in it
            assert "department" in it
            assert "column_name" in it
            assert "source_url" in it
            assert "publish_time" in it

    def test_notices_filter_department(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/api/notices", params={"department": "教务处"})
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["department"] == "教务处"

    def test_notices_filter_column(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/api/notices", params={"column": "通知公告"})
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["column_name"] == "通知公告"

    def test_notices_search_keyword(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/api/notices", params={"q": "考试"})
        assert r.status_code == 200
        d = r.json()
        assert d["total"] >= 0

    def test_notices_pagination(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r1 = c.get("/api/notices", params={"page": 1, "size": 5})
        r2 = c.get("/api/notices", params={"page": 2, "size": 5})
        assert r1.status_code == 200 and r2.status_code == 200
        # 两个页面的数据不应完全重复
        ids1 = {it["doc_id"] for it in r1.json()["items"]}
        ids2 = {it["doc_id"] for it in r2.json()["items"]}
        assert not (ids1 & ids2)

    def test_notices_size_capped(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/api/notices", params={"size": 999})
        assert r.json()["size"] == 100

    def test_notice_detail(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        lst = c.get("/api/notices", params={"size": 1}).json()
        doc_id = lst["items"][0]["doc_id"]
        r = c.get(f"/api/notices/{doc_id}")
        assert r.status_code == 200
        d = r.json()
        assert d["doc_id"] == doc_id
        assert "content" in d  # 详情接口应含正文

    def test_notice_detail_not_found(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/api/notices/not-exist-id-12345")
        assert r.status_code == 404


class TestPublicStats:
    def test_stats_public_shape(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/api/stats/public")
        assert r.status_code == 200
        d = r.json()
        assert "documents_total" in d
        assert "departments" in d
        assert "queries_today" in d

    def test_stats_public_no_sensitive(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        d = c.get("/api/stats/public").json()
        # 脱敏版不应暴露累计问答量
        assert "queries_total" not in d

    def test_stats_public_departments(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        d = c.get("/api/stats/public").json()
        assert isinstance(d["departments"], list)
        if d["departments"]:
            assert "department" in d["departments"][0]
            assert "cnt" in d["departments"][0]


class TestPublicHot:
    def test_hot_questions_ok(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        r = c.get("/api/stats/hot?limit=5")
        assert r.status_code == 200
        d = r.json()
        assert "items" in d
        assert len(d["items"]) <= 5

    def test_hot_limit_clamped(self):
        from fastapi.testclient import TestClient
        c = TestClient(app)
        # limit 超上限应被限制在 20 以内
        r = c.get("/api/stats/hot?limit=999")
        assert r.status_code == 200
        assert len(r.json()["items"]) <= 20
