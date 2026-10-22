"""检索层单元测试。

运行：python -m pytest tests/test_search.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrieval.search import _extract_keywords, search


class TestExtractKeywords:
    def test_synonym_expansion(self):
        kws = _extract_keywords("校巴线路")
        assert "校巴" in kws
        assert "班车" in kws
        assert "巴士" in kws

    def test_chinese_substrings(self):
        kws = _extract_keywords("选课报名")
        assert "选课" in kws
        assert "报名" in kws

    def test_long_query_not_single_token(self):
        kws = _extract_keywords("校园巴士运行线路怎么走")
        assert "校园" in kws
        assert "巴士" in kws
        assert "运行" in kws
        assert "线路" in kws

    def test_empty_query(self):
        kws = _extract_keywords("")
        assert len(kws) == 0


class TestSearch:
    def test_returns_list(self):
        results = search("选课", topk=3)
        assert isinstance(results, list)

    def test_baishi_query(self):
        results = search("报修电话", topk=5)
        assert len(results) > 0
        # 同义词扩充后"报修电话"也匹配"服务电话"等
        assert "报修" in results[0]["title"] or "服务电话" in results[0]["title"]

    def test_bus_query(self):
        results = search("校园巴士", topk=5)
        assert len(results) > 0
        assert "巴士" in results[0]["title"] or "班车" in results[0]["title"]

    def test_scholarship_query(self):
        results = search("奖学金助学金", topk=3)
        assert len(results) > 0
        assert "奖" in results[0]["title"]

    def test_result_fields(self):
        results = search("选课", topk=1)
        if results:
            r = results[0]
            assert "doc_id" in r
            assert "title" in r
            assert "department" in r
            assert "score" in r

    def test_empty_query(self):
        results = search("", topk=5)
        assert isinstance(results, list)

    def test_score_ordering(self):
        results = search("四六级报名", topk=5)
        if len(results) > 1:
            assert results[0]["score"] >= results[1]["score"]
