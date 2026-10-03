"""爬虫主入口：抓取站点栏目文章并落盘，支持列表栏目与静态单页。"""

import argparse
import json
from datetime import datetime

from crawler.config import SITES, RAW_DIR, CLEAN_DIR
from crawler.sudy import SdyCrawler
from crawler.cleaner import html_to_text


def _load_seen(path):
    if path.exists():
        return set(json.loads(path.read_text(encoding="utf-8")))
    return set()


def _save_seen(path, seen):
    path.write_text(json.dumps(sorted(seen)), encoding="utf-8")


def _save_article(crawler, site, site_raw_dir, clean_file, seen, href,
                  title_fallback, date, column_name):
    if "/page.htm" not in href:
        return
    aid = crawler.extract_article_id(href)
    if aid and aid in seen:
        return
    detail = crawler.parse_detail(crawler.fetch(href), href)
    source_url = href if href.startswith("http") else crawler.base_url + href
    record = {
        "id": aid or "",
        "title": detail["title"] or title_fallback,
        "source_url": source_url,
        "publish_time": detail["publish_time"] or date,
        "publisher": detail["publisher"],
        "department": site["department"],
        "column": column_name,
        "content": html_to_text(detail["content_html"]),
        "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    raw_record = {**record, "content_html": detail["content_html"]}
    raw_path = site_raw_dir / f"{aid or 'unknown'}.json"
    raw_path.write_text(
        json.dumps(raw_record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    clean_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    clean_file.flush()
    if aid:
        seen.add(aid)
    print(f"    已入库：{record['title'][:40]}")


def crawl_site(site_key, site, limit, delay):
    crawler = SdyCrawler(site["base_url"], delay=delay)
    site_raw_dir = RAW_DIR / site_key
    site_raw_dir.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    seen_path = site_raw_dir / "seen.json"
    seen = _load_seen(seen_path)

    clean_path = CLEAN_DIR / f"{site_key}.jsonl"
    clean_file = clean_path.open("a", encoding="utf-8")

    for column in site.get("columns", []):
        print(f"[{site['name']}] 抓取栏目：{column['name']} {column['list_path']}")
        collection = []
        page = 1
        while True:
            if limit and len(collection) >= limit:
                break
            html = crawler.fetch(crawler.list_page_url(column["list_path"], page))
            articles, total_pages = crawler.parse_list(html, column["list_path"])
            if not articles:
                break
            collection.extend(articles)
            if page >= total_pages:
                break
            page += 1

        if limit:
            collection = collection[:limit]

        for art in collection:
            _save_article(crawler, site, site_raw_dir, clean_file, seen,
                          art["url"], art["title"], art["date"], column["name"])

    for pg in site.get("pages", []):
        _save_article(crawler, site, site_raw_dir, clean_file, seen,
                      pg["url"], pg["name"], "", "政策")

    clean_file.close()
    _save_seen(seen_path, seen)
    print(f"[{site['name']}] 完成，累计 {len(seen)} 篇")


def main():
    parser = argparse.ArgumentParser(description="珠科百事通爬虫")
    parser.add_argument("--site", default="jiaowu", help="站点 key")
    parser.add_argument("--limit", type=int, default=0, help="每栏目最多抓取条数，0=全部")
    parser.add_argument("--delay", type=float, default=5, help="请求间隔秒")
    args = parser.parse_args()

    if args.site not in SITES:
        raise SystemExit(f"未知站点：{args.site}")
    crawl_site(args.site, SITES[args.site], args.limit, args.delay)


if __name__ == "__main__":
    main()