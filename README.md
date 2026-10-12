# 珠科百事通 —— 校务生活 RAG 智能问答平台

> RAGGO!!!!! ｜ 华为云码道 Agent 创新赛（珠海科技学院站）｜ 方向 05：RAG 知识库问答
>
> 给珠科 3.1 万在校生的校务问答助手：选课规则、报修电话、校巴时刻、奖助政策——一句话问，3 秒答，答案必带官方出处。

## 文档

| 文档 | 说明 |
|---|---|
| `docs/珠科百事通项目方案书.docx` | 选题论证、架构、功能清单、时间线 |
| `docs/RAGGO团队分工书.docx` | 三人分工、分阶段任务、每日常规 |

## 项目结构

```
├── crawler/      数据层：教务处/后勤处/招生办通知爬虫（ZY 主导）
├── retrieval/    检索层：FTS5 关键词路 + 语义向量路 + RRF 融合（ZY 主导）
├── api/          生成层：FastAPI 问答服务 + 引用强制校验（ZY 主导）
├── miniapp/      应用层：微信小程序学生端（ZC 主导）— 已搭骨架（首页搜索 + 结果页）
├── data/         爬取数据落地（原始副本不入库）
├── evaluation/   评测集：100+ 真实学生问答（HJQ 主导）
└── docs/         方案书与分工书
```

## 分工速览

- **ZY**（队长）：算法与架构——双路检索、RAG 链路、爬虫、CodeArts 流水线
- **ZC**：应用开发——小程序学生端、Web 管理后台、API 联调、部署
- **HJQ**：数据质量与用户体验——评测集（100+ 真实问题）、数据校验、试用组织、参赛材料

## 冲刺节奏（初赛截止 2026-10-23）

| 阶段 | 时间 | 里程碑 |
|---|---|---|
| 冲刺 1 | 10-02 ~ 10-05 | 码道环境开通、爬虫跑通、数据入库 |
| 冲刺 2 | 10-06 ~ 10-12 | 检索双路 + 生成层 + 小程序骨架 |
| 冲刺 3 | 10-13 ~ 10-19 | 联调 + 100 问评测 ≥ 85% |
| 提交冲刺 | 10-20 ~ 10-23 | 每日提交迭代，10-23 截止 |

详细任务见分工书。

## 快速开始

环境：Python 3.12+（依赖见 `requirements.txt`）

```bash
# 方式一：一键启动（推荐）
python start.py

# 方式二：分步运行
python -m pip install -r requirements.txt          # 装依赖
python -m crawler.run --site jiaowu                 # 爬教务处
python -m crawler.run --site houqin                 # 爬后勤处
python -m crawler.run --site zsb                    # 爬招生办
python -m retrieval.index                           # 数据入库
python -m uvicorn api.main:app --port 8000          # 启 API
```

### Docker 部署（评委一键启动）

```bash
# 构建镜像
docker build -t zhike-baishitong .

# 运行（data/ 运行时挂载，密钥经 .env 注入）
docker run -p 8000:8000 --env-file .env -v ./data:/app/data zhike-baishitong
```

- 镜像基于 `python:3.12-slim`，内置 HEALTHCHECK（每 30s 探测 `/health`），`docker ps` 可见 healthy 状态
- `data/` 通过 `-v` 挂载进容器，首次启动 `start.py` 自动建库，已有数据可直接复用
- 大模型与 embedding 密钥通过 `--env-file .env` 注入，勿提交 `.env`

测试：

```bash
# 健康检查
curl http://127.0.0.1:8000/health

# 问答
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"四六级考试什么时候报名","topk":5}'

# 评测（40 问）
python -m evaluation.runner --api http://127.0.0.1:8000
```

## 当前状态（2026-10-02）

| 层 | 状态 | 说明 |
|---|---|---|
| 数据层 | ✅ 199 篇 | 教务处 109 + 后勤处 87 + 招生办 3 |
| 检索层 | ✅ 混合路 | FTS5（数字/英文）+ LIKE（中文子串）+ 同义词扩展 |
| 生成层 | ✅ 抽取式 | 智能摘要提取（最相关句子 + 上下文），大模型生成待接华为云 MaaS |
| 应用层 | ✅ 骨架 | 微信小程序：首页搜索/热门/历史 + 结果页答案/置信度/出处 |
| 评测 | ✅ 40 问 100% | 覆盖教务/后勤/招生全部类别 |

## 开发约定

- **全部核心模块由团队自主设计与实现**：数据采集管线、混合检索算法、问答服务、微信小程序端均为成员手写完成
- 开发过程按赛事要求使用华为云码道 CodeArts 辅助开发（IDE 插件），过程记录归档于提交材料
- 仓库：GitCode 公开仓（remote 已配置）
- commit 信息写清楚做了什么；推送前本地跑通
- 数据文件（data/ 下爬取内容）不入库，只入库代码与配置
