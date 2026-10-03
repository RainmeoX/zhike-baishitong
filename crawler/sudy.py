"""苏迪 sudy CMS 通用解析器，适用于教务处/后勤处/官网。"""

import re
import time

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from crawler.config import USER_AGENT


class SdyCrawler:
    def __init__(self, base_url, delay=5, timeout=15):
        self.base_url = base_url.rstrip("/")
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch(self, url):
        url = urljoin(self.base_url + "/", url)
        last_err = None
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                resp.encoding = "utf-8"
                time.sleep(self.delay)
                return resp.text
            except requests.RequestException as err:
                last_err = err
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"抓取失败 {url}: {last_err}")

    def list_page_url(self, list_path, page):
        if page <= 1:
            return list_path
        return list_path.replace("/list.htm", f"/list{page}.htm")

    def parse_list(self, html, list_path):
        soup = BeautifulSoup(html, "lxml")
        articles = []
        seen = set()
        table = soup.select_one("table.wp_article_list_table")
        if table:
            for a in table.select("a[title]"):
                href = a.get("href", "")
                if "/page.htm" not in href or href in seen:
                    continue
                title = a.get("title", "").strip()
                if not title:
                    continue
                seen.add(href)
                date = ""
                sib = a.find_next_sibling("span")
                if sib:
                    date = sib.get_text(strip=True)
                articles.append({"title": title, "url": href, "date": date})
        else:
            for a in soup.select("a.column-news-item[href*='/page.htm']"):
                href = a.get("href", "")
                if href in seen:
                    continue
                title_el = a.select_one(".column-news-title")
                date_el = a.select_one(".column-news-date")
                title = title_el.get_text(strip=True) if title_el else ""
                date = date_el.get_text(strip=True) if date_el else ""
                if not title:
                    continue
                seen.add(href)
                articles.append({"title": title, "url": href, "date": date})
        return articles, self._parse_total_pages(soup)

    def _parse_total_pages(self, soup):
        em = soup.select_one("em.all_pages")
        if em and em.get_text(strip=True).isdigit():
            return int(em.get_text(strip=True))
        return 1

    def parse_detail(self, html, url):
        soup = BeautifulSoup(html, "lxml")
        title_el = soup.select_one("h2.article_title")
        title = title_el.get_text(strip=True) if title_el else ""

        attri_el = soup.select_one("div.article_attri")
        attri_text = attri_el.get_text(" ", strip=True) if attri_el else ""

        publish_time = ""
        m = re.search(r"发布时间[:：]\s*(\d{4}/\d{2}/\d{2})", attri_text)
        if m:
            publish_time = m.group(1)

        publisher = ""
        m = re.search(r"发布人[:：]\s*([^\s]+)", attri_text)
        if m:
            publisher = m.group(1)

        content_el = soup.select_one("div.article_content") or soup.select_one("div.wp_articlecontent")
        content_html = str(content_el) if content_el else ""

        return {
            "title": title,
            "publish_time": publish_time,
            "publisher": publisher,
            "content_html": content_html,
        }

    @staticmethod
    def extract_article_id(url):
        m = re.search(r"/c\d+a(\d+)/page\.htm", url)
        return m.group(1) if m else None