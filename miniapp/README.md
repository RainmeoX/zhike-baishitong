# miniapp 应用层

微信小程序学生端（ZC 主导）。

## 结构

```
miniapp/
├── app.js          全局逻辑（apiBaseUrl 配置）
├── app.json        全局配置（页面/tabBar）
├── app.wxss        全局样式
├── sitemap.json    索引配置
├── project.config.json  项目配置
├── pages/
│   ├── index/      首页（搜索框 + 热门问题 + 历史）
│   └── result/     结果页（答案 + 置信度 + 参考来源）
```

## 运行

1. 微信开发者工具导入 `miniapp/` 目录
2. 修改 `app.js` 中 `apiBaseUrl` 为实际服务地址（默认 `http://127.0.0.1:8000`）
3. 编译预览

## 对接说明

- 搜索：`POST /ask` 传入 `{question, topk}`
- 返回：`{answer, confidence, references[{title, department, column, source_url, score}]}`,
- 参考来源点击事件：复制 source_url 到剪贴板（后续可改为跳转外部浏览器）