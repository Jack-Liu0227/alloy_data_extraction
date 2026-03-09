# UI Viewer

这是一个纯前端、本地离线可用的 JSONL 可视化查看器。

它的目标不是替代数据处理 Pipeline，而是帮助你在本地快速检查抽取结果、定位异常记录、对比结构化字段和原始输出。

## 适用场景

- 抽取任务跑完后，快速浏览整批 JSONL 输出
- 按论文标题、路径或字段内容查找某一条记录
- 检查 `alloy_json` 是否被正确解析
- 对照原始 JSON 排查模型输出格式问题
- 在不启动后端服务的情况下，本地离线查看结果

## 打开方式

直接用浏览器打开 `index.html` 即可，不需要额外安装依赖，也不需要启动 Python 服务。

## 基本用法

1. 直接用浏览器打开 `index.html`
2. 拖拽或多选上传一个或多个 `.jsonl` 文件
3. 左侧选择文件与记录，右侧查看结构化字段和原始 JSON
4. 如有需要，可通过顶部搜索框按标题、路径、字段内容过滤记录
5. 点击字段区域内的 `Copy` 或 `Full View` 可复制内容或全屏查看

## 适用文件

- `cache/alloy_pipeline/alloy_extraction_step1.jsonl`
- `cache/alloy_pipeline/alloy_extraction_step2.jsonl`
- `cache/alloy_pipeline/pdf_sources.jsonl`

如果你还保留旧版缓存文件，例如 `cache/hea_pipeline/hea_extraction_step2.jsonl`，当前 UI 也兼容读取其中的旧字段名 `hea_json`。

## 页面结构

- 左侧顶部：文件导入、搜索框、统计信息
- 左侧中部：文件列表，用于切换不同 JSONL 文件
- 左侧下部：记录列表，用于选择具体样本
- 右侧概览：展示标题、来源、composition、processing 等摘要信息
- 右侧元信息：展示文件名、PDF 路径、Markdown 路径
- 右侧结构化字段：展示解析后的结构化 JSON 内容
- 右侧原始 JSON：展示该条记录的完整原始数据

## 当前能力

- 支持单选或多选批量上传
- 支持按标题、路径、字段内容搜索
- 自动解析每行 JSON 和 `alloy_json` 字段
- 同时显示摘要字段、解析后的 JSON、原始记录
- 支持复制字段内容
- 支持全屏查看原始 JSON 或字段内容
- 所有解析都在浏览器本地完成，不上传文件

## 推荐查看顺序

1. 先导入 `alloy_extraction_step2.jsonl` 看最终抽取结果
2. 如果发现字段缺失，再导入 `alloy_extraction_step1.jsonl` 对照 Markdown 转换阶段输出
3. 先看右侧“概览”确认主字段是否合理
4. 再看“结构化字段”检查 `alloy_json` 的解析结果
5. 最后看“原始 JSON”判断问题出在模型输出、字段映射还是上游输入

## 常见排查建议

- 如果某条记录显示 `parse failed`，优先检查原始 JSON 里的 `alloy_json` 或旧版 `hea_json` 是否是合法 JSON 字符串
- 如果能看到原始记录但结构化字段为空，通常说明该条输出没有通过 JSON 解析
- 如果搜索不到预期记录，先检查文件是否导入成功，以及搜索词是否出现在标题、路径或字段内容中
- 如果字段值显示为 `no information`，说明该字段在当前抽取结果中缺失或未识别到可靠信息

## 限制说明

- 当前是纯静态前端查看器，不会修改源文件
- 当前不支持直接编辑 JSONL 内容
- 大体量文件可以打开，但浏览器性能取决于本机内存和文件大小
