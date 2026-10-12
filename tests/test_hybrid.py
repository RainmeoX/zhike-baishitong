"""混合检索（hybrid_search）核心管线测试。

覆盖：返回结构、RRF 融合、路由标注、时效降权、topk 截断、
空查询兜底、关键词路独立可用、重排保序、routes_of 辅助函数。

运行：python -m pytest tests/test_hybrid.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrieval.hybrid import hybrid_search, routes_of, RRF_K
from retrieval.search import search as keyword_search


class TestHybridSearchBasic:
    """基础结构与返回值约束。"""

    def test_returns_list(self):
        results = hybrid_search("选课", topk=3)
        assert isinstance(results, list)

    def test_result_fields(self):
        """每条结果必须含核心字段。"""
        results = hybrid_search("宿舍报修", topk=3)
        if results:
            r = results[0]
            assert "doc_id" in r
            assert "title" in r
            assert "score" in r
            assert "routes" in r
            assert "final_score" in r

    def test_topk_limit(self):
        """返回数 ≤ topk。"""
        for k in (1, 3, 5, 10):
            results = hybrid_search("校巴", topk=k)
            assert len(results) <= k

    def test_empty_query_no_crash(self):
        """空查询不抛异常。"""
        results = hybrid_search("", topk=5)
        assert isinstance(results, list)

    def test_score_is_int(self):
        """RRF 融合分 ×1000 后应为整数。"""
        results = hybrid_search("奖学金", topk=3)
        if results:
            assert isinstance(results[0]["score"], int)


class TestHybridSearchOrdering:
    """排序与打分约束。"""

    def test_sorted_by_final_score(self):
        """结果按 final_score 降序排列。"""
        results = hybrid_search("四六级报名", topk=5)
        for i in range(len(results) - 1):
            assert results[i]["final_score"] >= results[i + 1]["final_score"]

    def test_final_score_range(self):
        """final_score 应在 [0, 1] 区间（blended × recency，两者均 ≤1）。"""
        results = hybrid_search("食堂", topk=5)
        for r in results:
            assert 0 <= r["final_score"] <= 1.0

    def test_results_not_empty_for_common_query(self):
        """常见查询应能检索到结果。"""
        results = hybrid_search("校巴线路", topk=5)
        assert len(results) > 0


class TestHybridSearchRoutes:
    """路由标注（kw=关键词路, sem=语义路）。"""

    def test_routes_contains_kw(self):
        """关键词路始终执行，routes 至少含 'kw'。"""
        results = hybrid_search("选课", topk=3)
        if results:
            assert "kw" in results[0]["routes"]

    def test_routes_format(self):
        """routes 为 kw/sem 的组合字符串。"""
        results = hybrid_search("宿舍", topk=5)
        for r in results:
            assert set(r["routes"]) <= {"k", "w", "s", "e", "m"}  # 只含这些字符

    def test_routes_of_helper(self):
        """routes_of 辅助函数返回 routes 字段。"""
        results = hybrid_search("奖学金", topk=3)
        if results:
            assert routes_of(results[0]) == results[0]["routes"]


class TestHybridSearchFallback:
    """降级与兜底行为。"""

    def test_keyword_fallback(self):
        """hybrid_search 结果应与 keyword_search 有交集（关键词路始终运行）。"""
        hy = hybrid_search("报修电话", topk=5)
        kw = keyword_search("报修电话", topk=5)
        if kw and hy:
            kw_ids = {str(r["doc_id"]) for r in kw}
            hy_ids = {str(r["doc_id"]) for r in hy}
            assert len(kw_ids & hy_ids) > 0

    def test_long_query(self):
        """长查询不崩溃。"""
        q = "请问珠海科技学院宿舍报修电话是多少号我想打电话报修空调坏了"
        results = hybrid_search(q, topk=5)
        assert isinstance(results, list)

    def test_special_chars_query(self):
        """含特殊字符的查询不崩溃。"""
        results = hybrid_search("水费&电费@#$", topk=3)
        assert isinstance(results, list)

    def test_very_long_topk(self):
        """topk 很大时不崩溃。"""
        results = hybrid_search("选课", topk=100)
        assert isinstance(results, list)


class TestHybridSearchRRF:
    """RRF 融合逻辑。"""

    def test_rrf_k_constant(self):
        """RRF_K 应为 60（项目约定）。"""
        assert RRF_K == 60

    def test_keyword_only_results_have_score(self):
        """纯关键词路结果 score > 0。"""
        results = hybrid_search("军训", topk=3)
        if results:
            assert results[0]["score"] > 0

    def test_different_queries_different_results(self):
        """不同查询应返回不同 top-1（非全返回同一结果）。"""
        r1 = hybrid_search("校巴", topk=1)
        r2 = hybrid_search("奖学金", topk=1)
        r3 = hybrid_search("四六级", topk=1)
        titles = set()
        for r in (r1, r2, r3):
            if r:
                titles.add(r[0]["title"])
        # 至少有两种不同 top-1
        assert len(titles) >= 2
