# retrieval 检索层

双路混合检索：
- 关键词路：SQLite FTS5 + 同义词表（复用琥珀经验，精确命中电话/时刻）
- 语义路：embedding → 向量库
- 融合：RRF → 重排 Top-K；时效降权（过期通知减权）

评测：evaluation/ 下的 100 问回归集，目标准确率 ≥ 85%
