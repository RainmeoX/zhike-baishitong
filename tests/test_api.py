"""API 层单元测试。

运行：python -m pytest tests/test_api.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pydantic import ValidationError
from api.main import _extract_snippet, AskRequest


class TestExtractSnippet:
    def test_empty_content(self):
        assert _extract_snippet("", "查询") == ""
        assert _extract_snippet(None, "查询") == ""

    def test_finds_relevant_sentence(self):
        content = "这是第一句话。选课报名时间为9月1日至9月15日。这是第三句话。"
        snippet = _extract_snippet(content, "选课报名")
        assert "选课报名" in snippet
        assert "9月1日" in snippet

    def test_max_length(self):
        content = "。".join([f"第{i}句话内容" for i in range(50)])
        snippet = _extract_snippet(content, "第25句话", max_len=100)
        assert len(snippet) <= 100

    def test_no_match_returns_first_sentence(self):
        content = "苹果香蕉橘子。葡萄西瓜。"
        snippet = _extract_snippet(content, "完全不相关")
        assert len(snippet) > 0

    def test_expands_context(self):
        content = "前置内容。选课时间安排。后续内容。更多内容。"
        snippet = _extract_snippet(content, "选课时间", max_len=200)
        assert "选课时间" in snippet


class TestAskRequestValidation:
    """输入校验测试。"""

    def test_valid_request(self):
        req = AskRequest(question="选课怎么操作", topk=5)
        assert req.question == "选课怎么操作"
        assert req.topk == 5

    def test_default_topk(self):
        req = AskRequest(question="校巴")
        assert req.topk == 5

    def test_empty_question_rejected(self):
        with pytest.raises(ValidationError):
            AskRequest(question="", topk=5)

    def test_blank_question_rejected(self):
        with pytest.raises(ValidationError):
            AskRequest(question="   ", topk=5)

    def test_question_stripped(self):
        req = AskRequest(question="  选课  ", topk=5)
        assert req.question == "选课"

    def test_question_too_long_rejected(self):
        with pytest.raises(ValidationError):
            AskRequest(question="x" * 501, topk=5)

    def test_question_max_length_accepted(self):
        req = AskRequest(question="x" * 500, topk=5)
        assert len(req.question) == 500

    def test_topk_too_small_rejected(self):
        with pytest.raises(ValidationError):
            AskRequest(question="选课", topk=0)

    def test_topk_too_large_rejected(self):
        with pytest.raises(ValidationError):
            AskRequest(question="选课", topk=21)

    def test_topk_boundary_accepted(self):
        req1 = AskRequest(question="选课", topk=1)
        req2 = AskRequest(question="选课", topk=20)
        assert req1.topk == 1
        assert req2.topk == 20
