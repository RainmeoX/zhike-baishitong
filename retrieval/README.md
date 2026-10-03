# retrieval 检索层

双路混合检索：
- 关键词路：SQLite FTS5 + 同义词表（复用琥珀经验，精确命中电话/时刻）
- 语义路：embedding → 向量库
- 融合：RRF → 重排 Top-K；时效降权（过期通知减权）

## 当前进度（关键词路已实现）

- `db.py`：SQLite `documents` 表 + `documents_fts`（FTS5）虚拟表
- `index.py`：`data/clean/*.jsonl` → SQLite 入库 + 建索引
- `search.py`：混合检索
  - FTS5 `MATCH` 精确命中电话号码/英文/数字（「报修电话」「四六级」场景）
  - `LIKE` 子串命中中文关键词 + 同义词扩展（校巴→班车/巴士、饭堂→食堂 等）
  - 打分：标题命中 +3、正文命中 +1、FTS5 命中 +10，按分排序取 Top-K

## 运行

```bash
# 入库（重复运行自动去重）
python -c "from retrieval.index import build_index; print(build_index())"

# 检索
python -c "from retrieval.search import search; import json; print(json.dumps(search('报修电话', topk=5), ensure_ascii=False, indent=2))"
```

- 依赖：标准库 `sqlite3`（FTS5 需 SQLite ≥ 3.34，本机 3.49）
- 数据库：`data/zcst.db`（不入库 git）

评测：evaluation/ 下的 100 问回归集，目标准确率 ≥ 85%
