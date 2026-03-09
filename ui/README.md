# UI Viewer

这是一个纯前端、本地离线可用的 JSONL 可视化查看器。

## 用法

1. 直接用浏览器打开 `index.html`
2. 拖拽或多选上传一个或多个 `.jsonl` 文件
3. 左侧选择文件与记录，右侧查看结构化字段和原始 JSON

## 适用文件

- `cache/alloy_pipeline/alloy_extraction_step1.jsonl`
- `cache/alloy_pipeline/alloy_extraction_step2.jsonl`
- `cache/alloy_pipeline/pdf_sources.jsonl`

## 当前能力

- 支持单选或多选批量上传
- 支持按标题、路径、字段内容搜索
- 自动解析每行 JSON 和 `alloy_json` 字段
- 同时显示摘要字段、解析后的 JSON、原始记录
