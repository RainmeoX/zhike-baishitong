# api 生成层

FastAPI 问答服务：
- POST /ask：问题 → 混合检索 → 大模型生成（强制引用）→ 答案 + 出处列表
- 置信度不足 → 返回兜底（对应部门电话）
- 大模型：华为云 MaaS API（比赛用云）；本地 vLLM 离线兜底

## 当前进度（骨架版）

- `main.py`：FastAPI 应用，`POST /ask` + `GET /health`
- 已接关键词检索路（`retrieval.search`），答案暂为「检索抽取式」（top1 正文片段 + 出处列表），**大模型生成能力待接入华为云 MaaS**
- 兜底：检索无结果时返回部门电话提示

## 运行

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"报修电话","topk":5}'
```

- 依赖：`fastapi`、`uvicorn`（见根 requirements.txt）
- 返回：`answer`、`confidence`、`references[{title,department,column,source_url,score}]`
