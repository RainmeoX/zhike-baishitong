# 贡献指南 —— 珠科百事通

## Git Commit 规范（Conventional Commits）

所有 commit message 必须遵循以下格式：

```
<type>[scope]: <description>

[body]

[footer]
```

### type（必填）

| type | 含义 | 例子 |
|------|------|------|
| `feat` | 新功能 | `feat(crawler): 招生站补加招生信息栏目` |
| `fix` | 修 bug | `fix(eval): 评测落盘symlink兼容Windows` |
| `refactor` | 重构（行为不变） | `refactor(hybrid): 检索评分逻辑抽取为独立函数` |
| `perf` | 性能优化 | `perf(embed): 批量embedding减少API调用` |
| `docs` | 文档 | `docs: 更新项目分析报告` |
| `test` | 测试 | `test: 补充hybrid检索边界用例` |
| `chore` | 杂项/构建/依赖 | `chore: 移除opencode.json` |
| `ci` | CI/CD | `ci: 添加自动部署workflow` |
| `style` | 格式调整（不改逻辑） | `style: 统一缩进为4空格` |
| `build` | 构建系统 | `build: 升级pytest到8.0` |

### scope（可选）

标明改动范围，建议用模块名：

```
feat(llm): 接入智谱GLM-4-Flash
fix(crawler): 修复招生站分页解析
perf(retrieval): 空内容文档评分策略优化
docs(eval): 补充评测集说明
```

常用 scope：`crawler` / `retrieval` / `llm` / `api` / `eval` / `web` / `miniapp` / `data`

### 规则

1. **一个 commit 只做一件事**（atomic）—— 一堆不相关改动拆成多个 commit
2. **description 用祈使句/动宾短语**：`接入` 而非 `接入了`，`修复` 而非 `修复了`
3. **subject 行 ≤ 72 字符**
4. **body 解释 what/why，不解释 how**（diff 已经展示了 how）
5. **body 每行 ≤ 100 字符**
6. **破坏性变更**加 `!`：`feat(api)!: /ask 返回结构变更`
7. **中文描述**，commit message 用中文

### 拆分示例

一堆改动涉及多件事时，按逻辑拆开：

```bash
# 第1个：LLM 相关
git add api/llm.py api/main.py
git commit -m "feat(llm): 接入智谱GLM-4-Flash替代已下线的deepseek-v4-flash

deepseek-v4-flash 返回 403（模型已下线），改用智谱 GLM-4-Flash（永久免费）。
llm.py 优先读 LLM_* 环境变量，向后兼容 HWMAAS_*。
main.py 传 top-k 多篇给 LLM 提供更丰富上下文。"

# 第2个：检索相关
git add retrieval/hybrid.py retrieval/search.py
git commit -m "perf(retrieval): 空内容文档评分策略+同义词扩充

空内容文档（图片/表格页）reranker 过度压分，改用 0.2*rerank+0.8*rrf 融合权重。
同义词 21→52 组，新增报修电话、三灶、体测等。"

# 第3个：爬虫相关
git add crawler/config.py
git commit -m "feat(crawler): 招生站补加招生信息和视频栏目"
```

### 反例

```
# ❌ 一锅端
git add -A
git commit -m "feat: 换LLM+优化检索+补爬虫"

# ❌ 太模糊
git commit -m "update"
git commit -m "修改了一些文件"
git commit -m "wip"

# ❌ 自造 type
git commit -m "fix+log: 修复超时并记录日志"
```
