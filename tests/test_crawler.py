"""爬虫层单元测试。

运行：python -m pytest tests/test_crawler.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.cleaner import clean_text, html_to_text
from crawler.config import SITES


class TestCleanText:
    def test_removes_zero_width(self):
        text = "选课\u200b报名"
        assert "\u200b" not in clean_text(text)

    def test_preserves_plain_text(self):
        assert clean_text("hello") == "hello"

    def test_empty(self):
        assert clean_text("") == ""
        assert clean_text(None) == ""


class TestHtmlToText:
    def test_removes_html_tags(self):
        assert html_to_text("<p>hello</p>") == "hello"

    def test_strips(self):
        result = html_to_text("  hello  ")
        assert "hello" in result

    def test_removes_script(self):
        result = html_to_text("<script>var x=1;</script><p>ok</p>")
        assert "var" not in result
        assert "ok" in result


class TestSitesConfig:
    def test_three_sites(self):
        assert len(SITES) == 3

    def test_site_keys(self):
        assert "jiaowu" in SITES
        assert "houqin" in SITES
        assert "zsb" in SITES

    def test_site_fields(self):
        for key, site in SITES.items():
            assert "base_url" in site
            assert "department" in site
            assert "columns" in site or "pages" in site
