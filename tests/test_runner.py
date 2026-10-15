"""评测运行器单元测试：引用正确性抽检相关函数。

运行：python -m pytest tests/test_runner.py -v
"""

import sqlite3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.runner import (
    _cited_sources,
    _load_title_content,
    _resolve_cited_doc,
    _citation_check,
    _point_matched,
)


class TestCitedSources:
    def test_llm_format(self):
        # LLM 答案末尾标注「（来源：部门-通知标题）」
        ans = "选课时间为9月1日。（来源：教务处-关于2025年秋季选课的通知）"
        assert _cited_sources(ans) == ["教务处-关于2025年秋季选课的通知"]

    def test_fallback_format(self):
        # 兜底答案形如「根据「标题」：摘要」
        ans = "根据「关于校巴调整的通知」：线路有变。"
        assert _cited_sources(ans) == ["关于校巴调整的通知"]

    def test_mixed_dedup(self):
        # 两种格式混用，重复出处去重；按模式顺序遍历（先「来源」后「根据」）保序
        ans = ("根据「通知A」：内容。（来源：教务处-通知A）"
               "（来源：教务处-通知A）（来源：后勤处-通知B）")
        assert _cited_sources(ans) == ["教务处-通知A", "后勤处-通知B", "通知A"]

    def test_empty_answer(self):
        assert _cited_sources("") == []
        assert _cited_sources(None) == []

    def test_no_citation(self):
        assert _cited_sources("普通回答，没有出处标注。") == []


class TestLoadTitleContent:
    def test_missing_db_returns_none(self, tmp_path):
        assert _load_title_content(tmp_path / "no_such.db") is None

    def test_empty_table_returns_none(self, tmp_path):
        db = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, "
                     "doc_id TEXT UNIQUE, title TEXT NOT NULL, content TEXT NOT NULL)")
        conn.commit()
        conn.close()
        assert _load_title_content(db) is None

    def test_valid_db_returns_mapping(self, tmp_path):
        db = tmp_path / "ok.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, "
                     "doc_id TEXT UNIQUE, title TEXT NOT NULL, content TEXT NOT NULL)")
        conn.execute("INSERT INTO documents (doc_id, title, content) VALUES (?, ?, ?)",
                     ("d1", "选课通知", "选课时间为9月1日至9月5日。"))
        conn.commit()
        conn.close()
        mapping = _load_title_content(db)
        assert mapping == {"选课通知": "选课时间为9月1日至9月5日。"}


class TestResolveCitedDoc:
    def setup_method(self):
        self.tc = {"关于2025年秋季选课的通知": "选课时间9月1日。",
                   "校巴线路调整公告": "线路有变。"}

    def test_exact_match(self):
        assert _resolve_cited_doc("校巴线路调整公告", self.tc) == "校巴线路调整公告"

    def test_department_prefix(self):
        # 「部门-标题」出处：标题包含于出处串
        assert _resolve_cited_doc("教务处-关于2025年秋季选课的通知", self.tc) \
            == "关于2025年秋季选课的通知"

    def test_tail_suffix_match(self):
        # 出处串比标题长且标题不在出处串中时，取「-」后缀匹配
        assert _resolve_cited_doc("后勤处-校巴线路调整公告", self.tc) == "校巴线路调整公告"

    def test_no_match_returns_none(self):
        assert _resolve_cited_doc("完全不相关的出处", self.tc) is None


class TestCitationCheck:
    def setup_method(self):
        self.tc = {"关于2025年秋季选课的通知": "选课时间为9月1日至9月5日，请登录教务系统。",
                   "校巴线路调整公告": "校巴线路有调整，新增线路三途经南门。"}

    def test_none_mapping_skips(self):
        assert _citation_check("任意答案", "选课", None) is None

    def test_correct_citation(self):
        # 被引文档正文含期望要点 → 正确
        ans = "选课9月1日开始。（来源：教务处-关于2025年秋季选课的通知）"
        total, ok = _citation_check(ans, "选课时间", self.tc)
        assert (total, ok) == (1, 1)

    def test_wrong_citation(self):
        # 被引文档正文不含期望要点 → 不正确
        ans = "校巴有变化。（来源：后勤处-校巴线路调整公告）"
        total, ok = _citation_check(ans, "选课时间", self.tc)
        assert (total, ok) == (1, 0)

    def test_unresolvable_source_counts_wrong(self):
        # 出处解析不到库内文档 → 计为不正确（无法验证即不可信）
        ans = "答案。（来源：教务处-不存在的通知）"
        total, ok = _citation_check(ans, "选课时间", self.tc)
        assert (total, ok) == (1, 0)

    def test_no_citation_zero_total(self):
        total, ok = _citation_check("没有出处的回答", "选课时间", self.tc)
        assert (total, ok) == (0, 0)

    def test_multiple_citations(self):
        ans = ("选课9月1日开始。（来源：教务处-关于2025年秋季选课的通知）"
               "校巴新增线路。（来源：后勤处-校巴线路调整公告）")
        total, ok = _citation_check(ans, "选课时间、校巴线路", self.tc)
        assert (total, ok) == (2, 2)


class TestPointMatched:
    def test_short_point_exact(self):
        assert _point_matched("选课", "请尽快完成选课") is True
        assert _point_matched("选课", "没有相关内容") is False

    def test_long_point_fuzzy(self):
        # 长要点按子串覆盖率 ≥30% 模糊匹配
        assert _point_matched("选课时间为9月1日至9月5日", "选课时间为9月1日至9月5日，请登录系统") is True
