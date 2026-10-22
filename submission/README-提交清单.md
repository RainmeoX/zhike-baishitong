# 提交打包清单（初赛 10-23 前执行）

压缩包命名：`专业组+珠科百事通+RAGGO!!!!!+v1.0+<ZY手机号>.zip`（组别按组委会对队长专业的审核结果定）

**打包命令**：`python submission/pack.py --phone <ZY手机号>`
**验证命令**：`python submission/verify.py`

| 目录 | 内容 | 责任人 | 状态 |
|---|---|---|---|
| ppt/ | 作品介绍 PPT：场景背景、功能架构、核心亮点、码道应用说明 | HJQ 主笔、ZY 审 | 待做 |
| project/ | 完整工程源码（含 data/ 数据库 + .env.example，可一键复现） | ZY | ✅ 已打包（375 文件，3.1 MB） |
| video/ | 演示视频 ≤3 分钟（核心功能操作全流程） | ZC 录、HJQ 写脚本 | 待做 |
| codearts_proof/ | 码道使用证明：AI 对话与 Prompt 截图、代码生成/重构/排错记录 | **全员每周归档** | 持续 |
| readme/ | 部署说明文档（环境依赖、一键安装、部署步骤、开源组件、码道应用总结） | ZY | ✅ 已完成（部署说明.md） |

## project/ 打包内容

| 内容 | 说明 |
|------|------|
| 源码 | api/ crawler/ retrieval/ evaluation/ miniapp/ web/ tests/ |
| 数据 | data/zcst.db (2.5MB) + data/vectors.db (6.2MB) + data/clean/*.jsonl (3 站 286 篇) |
| 评测结果 | evaluation/results/latest.json (40/40 = 100%) |
| 配置 | .env.example（模板，不含密钥）、requirements.txt、start.py |
| 文档 | readme/部署说明.md、docs/、AGENTS.md、CONTRIBUTING.md、README.md |

**安全检查**：.env（真实密钥）已排除，不会打包 ✓

加分项：readme 里附 GitCode 仓库地址与作品展览馆发布链接。
