"""HTML 正文清洗为纯文本。"""

import re

from bs4 import BeautifulSoup

_ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\ufeff]")


def clean_text(text):
    if not text:
        return ""
    return _ZERO_WIDTH.sub("", text)


def html_to_text(html):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for p in soup.find_all("p"):
        p.append("\n")
    text = soup.get_text()
    lines = [re.sub(r"[ \t\u3000]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return clean_text("\n".join(lines))