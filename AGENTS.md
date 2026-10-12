# AGENTS.md —— 珠科百事通 · AI 协作规范

> 本文件由码道 CodeArts 智能体在会话开始时自动读取。请严格遵守以下内容再动手。

## 项目概述

面向珠海科技学院 3.1 万在校生的校务生活 RAG 智能问答平台「珠科百事通」。
数据流：爬虫采集官方通知（教务处/后勤处/招生网）→ 清洗入库 → 混合检索
（FTS5 关键词路 + bge-m3 语义路 → RRF 融合 → 重排 → 时效降权）→ 大模型生成带出处的回答。

## 目录结构

```
crawler/      数据层：三站爬虫与清洗（字段必须含 id/title/source_url/publish_time/publisher/department/column/content/crawled_at）
retrieval/    检索层：search.py 关键词路 / embedding.py+vector.py 语义路 / hybrid.py RRF 融合 / rerank.py 重排
api/          生成层：FastAPI 问答服务（POST /ask），llm.py 华为云 MaaS 接入
miniapp/      微信小程序学生端
evaluation/   评测：questions.csv（40 问）+ runner.py（python -m evaluation.runner）
web/          网页测试台（GET / 直接打开）
data/         爬取数据与数据库（不入 git）
docs/ 日志/    项目文档与每日日志
```

## 常用命令

```bash
python start.py                                  # 一键启动（依赖安装+建库+起服务）
python -m pytest tests/ -q                       # 跑测试（当前 25 个，改代码后必须全过）
python -m crawler.run --site jiaowu|houqin|zsb   # 爬虫
python -m retrieval.index                        # 数据入库
python -m retrieval.hybrid --rebuild             # 重建语义向量库
python -m evaluation.runner --api http://127.0.0.1:8000   # 跑评测（40 问，目标 ≥85%）
python -m uvicorn api.main:app --port 8000       # 起 API
```

## 环境要求

- Python 3.12：`C:\Users\Rainmeo\AppData\Local\Programs\Python\Python312\python.exe`
- 已装依赖：fastapi / uvicorn / requests / beautifulsoup4 / lxml / pytest
- 大模型与 embedding 走华为云 MaaS（密钥在项目 .env，勿打印、勿提交）

## 编码纪律（必须遵守）

1. **先跑测试再交付**：任何代码改动后 `python -m pytest tests/ -q` 必须全过
2. **数据字段一致性**：新爬取数据字段与现有 JSONL 完全一致，缺字段宁可不入库
3. **爬虫礼仪**：请求间隔 ≥5 秒、带 UA 和 Referer、只爬公开通知
4. **不编造数据**：评测集问题必须来自真实学生视角，期望答案必须对应真实通知内容
5. **路径中性**：代码/脚本/文档中的 Python 一律用上面的系统 Python 3.12 路径，
   不引用任何个人目录或私有工具链路径；叙述中 AI 工具只提"华为云码道 CodeArts"
6. **中文注释**：核心逻辑注释用中文，commit message 遵循 Conventional Commits 规范（详见 CONTRIBUTING.md）
7. **敏感词自查**：提交前对改动文件执行 `grep -ri` 检查（密钥/密钥变量值/内部路径），有命中先报告再改
8. **原子提交**：一个 commit 只做一件事，一堆不相关改动拆成多个 commit，禁止 `git add -A` 一锅端
9. **推送节奏**：平时只做本地原子 commit，每完成一个完整功能闭环
   （代码+测试全过+验证）才推一次远程；不逐 commit 推送、不每天例行推送、
   不主动催推送（换机器等怕丢工作的场景除外，详见 CONTRIBUTING.md）

## 协作方式

- 拿不准的改动先给方案（含取舍），确认后再动手
- 大改动分小步提交，每步可运行
- 遇到报错先贴完整堆栈分析根因，不盲改
