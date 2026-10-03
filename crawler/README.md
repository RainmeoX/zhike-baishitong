# crawler 数据层

目标子站（苏迪 sudy CMS，共用 `sudy.py` 解析器）：

| key | 站点 | 栏目 | 问答场景 |
|---|---|---|---|
| jiaowu | 教务处 jx.zcst.edu.cn | 通知公告/考试信息/选课管理/学籍管理/规章制度 | 选课·考试·重修·学籍 |
| houqin | 后勤处 hq.zcst.edu.cn | 通知公告/服务指南/后勤服务/规章制度 | 报修·电话·班车·食堂 |
| zsb | 招生办 zsb.zcst.edu.cn | 奖助学金/转专业/招生章程（静态页） | 奖助政策 |

> 学校官网 www.zcst.edu.cn 以新闻宣传为主、对校务问答价值低，暂缓；后续如需可加「学校要闻」。

约定：
- 抓取间隔 ≥5 秒，只爬公开通知
- 每条数据必须带：标题、正文、发布时间、来源 URL、部门
- 原始 JSON 落 data/raw/<site>/，清洗后落 data/clean/<site>.jsonl（均不入库）

## 运行

```bash
# 全量抓取各站点
python -m crawler.run --site jiaowu
python -m crawler.run --site houqin
python -m crawler.run --site zsb

# 小批量测试（每栏目限 2 条，间隔 3 秒）
python -m crawler.run --site houqin --limit 2 --delay 3
```

- 依赖：`requests`、`beautifulsoup4`、`lxml`（见根 requirements.txt）
- 已抓文章写入 `data/raw/<site>/seen.json` 去重，重复运行自动跳过
- 解析器兼容三种列表模板（`table.wp_article_list_table` / `a.column-news-item` / 静态 `pages`）
