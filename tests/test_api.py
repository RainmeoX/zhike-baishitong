"""API 层单元测试。

运行：python -m pytest tests/test_api.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pydantic import ValidationError
from api.main import _extract_snippet, _calc_confidence, _is_refusal_answer, AskRequest


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


class TestConfidence:
    """置信度归一化：精排分映射，修复旧实现恒 100% 的问题。"""

    def test_high_rerank_score(self):
        assert _calc_confidence({"rerank_score": 0.9, "final_score": 0.8}) == 0.9

    def test_capped_at_095(self):
        # rerank 分异常高（>1）也封顶 0.95，不再出现 1.0
        assert _calc_confidence({"rerank_score": 2.0}) == 0.95
        assert _calc_confidence({"rerank_score": 16}) == 0.95  # 旧 bug 的粗排分误入也不恒 1.0

    def test_fallback_to_final_score(self):
        # rerank 服务失败时无 rerank_score，回退 final_score
        assert _calc_confidence({"final_score": 0.6, "score": 16}) == 0.6

    def test_floor_at_005(self):
        assert _calc_confidence({}) == 0.05
        assert _calc_confidence({"rerank_score": 0}) == 0.05

    def test_weak_relevance_low_confidence(self):
        # 弱相关（超纲题常见）分低 → 置信度明显低于正常题，形成区分度
        assert _calc_confidence({"rerank_score": 0.2}) == 0.2


class TestRefusalDetection:
    """LLM 拒答判定：严格关键词，须拦截"个人知识"式泄漏且不误伤正常回答。"""

    def test_standard_refusal(self):
        assert _is_refusal_answer("暂未检索到相关通知。") is True
        assert _is_refusal_answer("抱歉，知识库中未找到相关信息。") is True
        assert _is_refusal_answer("参考内容不足以回答该问题。") is True

    def test_separated_wording(self):
        # LLM 分离式措辞："没有…提及"间隔变体
        assert _is_refusal_answer("没有在提供的参考内容中提及相关安排。") is True
        assert _is_refusal_answer("参考通知里没有明确提到报名费标准。") is True

    def test_normal_answer_not_refused(self):
        # 正常回答含"建议联系/致电"等字样，不得误判为拒答
        assert _is_refusal_answer(
            "空调报修可联系宿管处，建议拨打后勤处电话 7626267。"
            "（来源：后勤处-通知）"
        ) is False
        assert _is_refusal_answer(
            "四六级报名时间为9月15日至9月19日，记得按时缴费。"
            "（来源：教务处-关于开展2026年下半年全国大学英语四、六级考试报名工作的通知）"
        ) is False

    def test_empty_text(self):
        assert _is_refusal_answer("") is False
        assert _is_refusal_answer(None) is False
