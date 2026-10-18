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
    _is_refusal,
    run_eval,
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


class TestIsRefusal:
    def test_fallback_answer_is_refusal(self):
        # 兜底答案「暂未检索到…建议联系…」
        ans = "抱歉，当前知识库暂未检索到与您问题相关的官方信息。建议联系对应部门获取最新答复。"
        assert _is_refusal(ans) is True

    def test_llm_insufficient_is_refusal(self):
        # LLM 说明不足类回答
        assert _is_refusal("参考内容不足以回答该问题，建议联系教务处。") is True

    def test_llm_varied_wording_is_refusal(self):
        # 强化 prompt 后 LLM 的多样化拒答措辞（真实 badcase 回归）
        assert _is_refusal("暂时没有在提供的参考内容中提及，建议你直接联系后勤处。") is True
        assert _is_refusal("参考内容中没有明确提到，建议你联系相关部门。") is True
        # 分离式措辞：关键词被间隔（「没有…提及」「建议…联系」）
        assert _is_refusal("参考内容中没有明确说明这一点，建议你直接联系相关部门咨询。") is True

    def test_fabricated_answer_not_refusal(self):
        # 真编造（给出具体数据+假来源）不应被误判为拒答
        ans = "图书馆借书超期罚款是按照每本书每天0.5元来计算的哦。（来源：后勤处-图书馆借阅规则）"
        assert _is_refusal(ans) is False

    def test_normal_answer_not_refusal(self):
        assert _is_refusal("选课时间为9月1日。（来源：教务处-选课通知）") is False

    def test_empty_answer_not_refusal(self):
        assert _is_refusal("") is False


class TestRunEvalRefusal:
    """拒答题（期望要点为空）不计入 Hit Rate 分母，单独统计拒答成功率。"""

    def _write_csv(self, tmp_path, rows):
        csv_path = tmp_path / "questions.csv"
        lines = ["id,问题,类别,期望答案要点,来源"]
        lines.extend(rows)
        csv_path.write_text("\n".join(lines), encoding="utf-8")
        return str(csv_path)

    def _patch(self, tmp_path, monkeypatch, responses):
        def fake_post(url, json=None, timeout=60):
            class R:
                status_code = 200

                def json(self):
                    return responses[json["question"]]
            return R()

        monkeypatch.setattr("evaluation.runner.requests.post", fake_post)
        # 库指向不存在路径，跳过引用抽检，保持测试封闭
        monkeypatch.setattr("evaluation.runner.DB_PATH", tmp_path / "no_such.db")

    def test_refusal_counted_separately(self, tmp_path, monkeypatch):
        # 1 道可答题命中 + 1 道拒答题正确说明：Hit Rate 分母只算可答题
        csv_path = self._write_csv(tmp_path, [
            "1,报修电话是多少,后勤-报修,报修电话,学校通知",
            "2,校长手机号是多少,陷阱,,学校通知",
        ])
        self._patch(tmp_path, monkeypatch, {
            "报修电话是多少": {
                "answer": "报修电话为0756-7626267。（来源：后勤处-报修电话指南）",
                "references": [{"title": "报修电话指南", "department": "后勤处", "column": "通知"}],
                "confidence": 0.9,
            },
            "校长手机号是多少": {
                "answer": "抱歉，当前知识库暂未检索到与您问题相关的官方信息。建议联系对应部门。",
                "references": [],
                "confidence": 0.0,
            },
        })
        rate, mrr, recall_at_k, cite_prec, refusal_rate, details = run_eval("http://x", csv_path)
        assert rate == 100.0
        assert refusal_rate == 100.0
        assert cite_prec is None
        assert len(details) == 2
        assert details[1]["type"] == "refusal"
        assert details[1]["refusal_ok"] is True
        assert details[1]["hit"] is True

    def test_fabricated_answer_fails_refusal(self, tmp_path, monkeypatch):
        # 拒答题编造答案（无拒答标记）→ 拒答失败
        csv_path = self._write_csv(tmp_path, [
            "1,校长手机号是多少,陷阱,,学校通知",
        ])
        self._patch(tmp_path, monkeypatch, {
            "校长手机号是多少": {
                "answer": "校长手机号是13800138000。",
                "references": [{"title": "某通知", "department": "教务处", "column": "通知"}],
                "confidence": 0.8,
            },
        })
        rate, mrr, recall_at_k, cite_prec, refusal_rate, details = run_eval("http://x", csv_path)
        assert refusal_rate == 0.0
        assert details[0]["refusal_ok"] is False
        assert details[0]["hit"] is False

    def test_no_refusal_rows_rate_is_none(self, tmp_path, monkeypatch):
        # 全部为可答题时拒答成功率为 None（不适用）
        csv_path = self._write_csv(tmp_path, [
            "1,报修电话是多少,后勤-报修,报修电话,学校通知",
        ])
        self._patch(tmp_path, monkeypatch, {
            "报修电话是多少": {
                "answer": "报修电话为0756-7626267。（来源：后勤处-报修电话指南）",
                "references": [{"title": "报修电话指南", "department": "后勤处", "column": "通知"}],
                "confidence": 0.9,
            },
        })
        rate, mrr, recall_at_k, cite_prec, refusal_rate, details = run_eval("http://x", csv_path)
        assert rate == 100.0
        assert refusal_rate is None
