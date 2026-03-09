# Alloy Data Extraction

面向合金材料文献的 DataFlow 抽取项目。  
输入是一批 PDF，输出是 Markdown 中间结果和结构化字段 JSON。

当前仓库的定位是通用合金文献抽取框架：

- `operators/core/` 中的核心抽取算子不绑定具体合金体系
- 通过替换 Prompt、Schema 和领域算子，可以扩展到任意合金方向
- 默认提供的主入口已经统一为通用合金抽取命名

默认文档为中文。英文文档见 [README_EN.md](/D:/XJTU/ImportantFile/auto-design-alloy/alloy_data_extraction/README_EN.md)。

本项目当前代码风格尽量对齐北大开源 [DataFlow 中文文档](https://opendcai.github.io/DataFlow-Doc/zh/) 中推荐的写法：

- `PipelineABC` 子类只负责声明算子编排
- 先 `compile()`，再 `forward(resume_step=...)`
- `OperatorABC.run()` 使用标准参数命名 `storage` / `input_key` / `output_key`
- `PromptABC` 单独定义，避免把提示词硬编码在 Pipeline 中
- 领域算子建立在可复用的 core 算子之上

参考文档：

- [框架总览](https://opendcai.github.io/DataFlow-Doc/zh/framework/pipeline/)
- [断点恢复](https://opendcai.github.io/DataFlow-Doc/zh/guide/resume/)
- [自定义 Prompt/Operator/Pipeline](https://opendcai.github.io/DataFlow-Doc/zh/framework/self_define/)

## 1. 项目目标

本仓库做两件事：

1. 将 PDF 批量转为 Markdown
2. 从 Markdown 中提取结构化合金信息

当前默认抽取 4 个字段：

- `composition`
- `processing`
- `properties`
- `test_conditions`

如果文献中缺失某项，统一填入 `"no information"`。

如果你需要支持别的合金体系，通常只需要替换以下几层：

- `prompts/core.py` 中的抽取提示词
- `operators/domain/` 下的领域封装算子
- `pipelines/` 下的具体业务 Pipeline

## 2. 代码结构

```text
alloy_data_extraction/
├─ alloy_data_extraction/
│  ├─ __init__.py
│  ├─ provider.py
│  ├─ version.py
│  ├─ operators/
│  │  ├─ core/
│  │  │  └─ markdown_json_schema_extractor.py
│  │  └─ domain/
│  │     └─ alloy_info_extractor.py
│  ├─ pipelines/
│  │  └─ alloy_pdf_pipeline.py
│  ├─ prompts/
│  │  └─ core.py
│  └─ utils/
│     └─ manifest.py
├─ cache/
├─ scripts/
│  └─ build_pipeline_input.py
├─ requirements.txt
└─ README.md
```

各目录职责如下：

- `provider.py`
  负责读取 `.env` 并创建 `APILLMServing_request`
- `prompts/core.py`
  负责定义通用合金抽取 Prompt
- `operators/core/`
  放通用可复用算子，不绑定具体合金领域
- `operators/domain/`
  放领域封装算子，当前仓库内置的是通用合金抽取算子
- `pipelines/`
  放符合 DataFlow 风格的流水线编排，当前内置主入口为通用合金 Pipeline
- `utils/manifest.py`
  负责构建输入 JSONL 清单
- `scripts/`
  放独立可执行脚本

## 3. 环境准备

### 3.1 Python

建议使用 Python 3.10 及以上版本，并在独立虚拟环境中安装依赖。

### 3.2 安装依赖

```bash
pip install -r requirements.txt
```

当前依赖很少，核心依赖只有：

- `open-dataflow`

如果你使用的是 `conda` 或 `venv`，只要保证当前环境能正确导入 `dataflow` 即可。

## 4. LLM 配置

### 4.1 配置方式

当前代码库只读取一组统一环境变量，不再区分多个 provider 前缀。

代码入口在 [alloy_data_extraction/provider.py](/D:/XJTU/ImportantFile/auto-design-alloy/alloy_data_extraction/alloy_data_extraction/provider.py)。

运行时会读取：

- `DF_API_KEY`
- `DF_MODEL_ID`
- `DF_BASE_URL` 或 `DF_BASE_URLS`

说明：

- 推荐只使用 `DF_BASE_URL`
- 如果 `DF_BASE_URLS` 里写了多个 URL，当前实现只取第一个
- 如果 URL 没有以 `/v1/chat/completions` 结尾，代码会自动补齐成 OpenAI-compatible 请求地址

### 4.2 `.env.example` 与 `.env`

仓库已提供 [.env.example](/D:/XJTU/ImportantFile/auto-design-alloy/alloy_data_extraction/.env.example) 作为模板。

你可以这样初始化：

```bash
copy .env.example .env
```

模板内容如下：

```env
DF_API_KEY=your_api_key
DF_BASE_URL=https://api.deepseek.com/v1
DF_MODEL_ID=deepseek-chat
```

如果你想切换到别的模型服务，只需要改这 3 个值，不需要再改变量名。

### 4.3 配置排查建议

如果模型请求没有成功，优先检查这几项：

- `.env` 文件是否放在项目根目录，或者 `--env-file` 是否传了正确路径
- `DF_API_KEY`、`DF_MODEL_ID`、`DF_BASE_URL` 是否都有值
- `DF_BASE_URL` 是否真的是 OpenAI-compatible 接口
- 本地模型场景下，本地推理服务是否已经启动

### 4.4 当前 LLM 调用方式

项目通过 `dataflow.serving.APILLMServing_request` 发起请求。  
抽取算子会优先尝试传入 `json_schema`，如果某些兼容接口不支持该能力，会自动降级为普通文本返回，再做 JSON 解析。

## 5. DataFlow 风格实现说明

### 5.1 Prompt

[alloy_data_extraction/prompts/core.py](/D:/XJTU/ImportantFile/auto-design-alloy/alloy_data_extraction/alloy_data_extraction/prompts/core.py)

- `AlloyExtractionPrompt` 继承 `PromptABC`
- `build_prompt(markdown_text=...)` 只负责拼装输入
- `system_prompt` 作为 Prompt 对象的一部分保存

### 5.2 Core Operator

[alloy_data_extraction/operators/core/markdown_json_schema_extractor.py](/D:/XJTU/ImportantFile/auto-design-alloy/alloy_data_extraction/alloy_data_extraction/operators/core/markdown_json_schema_extractor.py)

这是一个通用算子，负责：

- 从 `input_key` 对应列读取 Markdown 路径
- 读取文件内容
- 调用 LLM
- 根据默认字段补全缺失值
- 将结构化结果写回 `output_key` 和各个字段列

它不绑定具体合金体系，因此后续可以复用于任意合金或其他材料方向。

### 5.3 Domain Operator

[alloy_data_extraction/operators/domain/alloy_info_extractor.py](/D:/XJTU/ImportantFile/auto-design-alloy/alloy_data_extraction/alloy_data_extraction/operators/domain/alloy_info_extractor.py)

这是当前仓库内置的通用合金领域算子，负责：

- 绑定通用合金 Prompt
- 绑定通用合金 JSON Schema
- 绑定默认输出字段
- 默认输出列名为 `alloy_json`

它本质上是对 core 算子的二次封装，这种写法更接近 DataFlow 官方推荐的“通用能力 + 领域配置”分层。

### 5.4 Pipeline

[alloy_data_extraction/pipelines/alloy_pdf_pipeline.py](/D:/XJTU/ImportantFile/auto-design-alloy/alloy_data_extraction/alloy_data_extraction/pipelines/alloy_pdf_pipeline.py)

Pipeline 只做编排，不在 `forward()` 内写复杂业务逻辑：

1. PDF -> Markdown
2. Markdown -> 合金字段抽取

并按 DataFlow 习惯使用：

```python
pipeline = AlloyPdfExtractionPipeline(...)
pipeline.compile()
pipeline.forward(resume_step=resume_step)
```

## 6. 输入数据准备

### 6.1 生成输入清单

先把 PDF 目录整理成 DataFlow 可读的 JSONL：

```bash
python scripts/build_pipeline_input.py \
  --input-root "D:\XJTU\ImportantFile\auto-design-alloy\database\papers\arxiv" \
  --output "./cache/alloy_pipeline/pdf_sources.jsonl"
```

生成后的 JSONL 每行形如：

```json
{"source": "D:/path/to/paper.pdf"}
```

### 6.2 直接由 Pipeline 自动生成

即使不先手工执行脚本，Pipeline 也会在初始化时自动调用 `build_pdf_manifest(...)` 生成同样的输入清单。  
脚本的意义主要是为了：

- 提前检查输入目录
- 先单独确认将要处理哪些 PDF
- 调试时复用固定输入清单

## 7. 运行方式

### 7.1 执行主 Pipeline

```bash
python -m alloy_data_extraction.pipelines.alloy_pdf_pipeline \
  --pdf-root "D:\XJTU\ImportantFile\auto-design-alloy\database\papers\arxiv" \
  --cache-path "./cache/alloy_pipeline" \
  --md-output-dir "./cache/alloy_pipeline/md" \
  --env-file ".env" \
  --resume-step auto
```

### 7.2 常用参数

- `--pdf-root`
  PDF 根目录
- `--cache-path`
  DataFlow 中间缓存目录
- `--md-output-dir`
  Markdown 中间结果目录
- `--env-file`
  `.env` 路径
- `--mineru-backend`
  传给 PDF 转 Markdown 算子的后端名
- `--max-workers`
  LLM 并发 worker 数
- `--max-retries`
  LLM 请求最大重试次数
- `--resume-step`
  从指定步骤恢复，或使用 `auto`

## 8. 断点恢复

断点恢复逻辑位于 [alloy_data_extraction/pipelines/alloy_pdf_pipeline.py](/D:/XJTU/ImportantFile/auto-design-alloy/alloy_data_extraction/alloy_data_extraction/pipelines/alloy_pdf_pipeline.py) 中的 `resolve_resume_step(...)`。

当前约定：

- `step1` 对应 PDF -> Markdown
- `step2` 对应 Markdown -> 合金字段抽取

自动恢复规则：

1. 如果 `step2` 存在且完整，则从第 2 步状态恢复
2. 如果 `step2` 存在但行数少于 `step1`，视为第 2 步未完成，恢复到第 1 步之后
3. 如果只有 `step1`，则从第 1 步之后恢复
4. 如果都没有，则从头开始

手动指定恢复：

```bash
python -m alloy_data_extraction.pipelines.alloy_pdf_pipeline --resume-step 1
```

## 9. 输出结果

默认缓存目录是：

```text
./cache/alloy_pipeline
```

关键输出包括：

- `pdf_sources.jsonl`
  输入 PDF 清单
- `alloy_extraction_step1.jsonl`
  Markdown 转换阶段输出
- `alloy_extraction_step2.jsonl`
  抽取阶段输出
- `md/`
  Markdown 中间文件及相关解析结果

最终抽取结果包含：

- `alloy_json`
- `composition`
- `processing`
- `properties`
- `test_conditions`

其中 `alloy_json` 是单列 JSON 字符串，其他 4 列是拆分后的字段列。

## 10. UI 查看器说明

仓库自带一个本地离线可用的 JSONL 查看器，位于 [ui/index.html](/D:/XJTU/ImportantFile/auto-design-alloy/alloy_data_extraction/ui/index.html)。

### 10.1 打开方式

直接在浏览器中打开 `ui/index.html` 即可，不依赖后端服务。

### 10.2 适合查看的文件

- `cache/alloy_pipeline/pdf_sources.jsonl`
- `cache/alloy_pipeline/alloy_extraction_step1.jsonl`
- `cache/alloy_pipeline/alloy_extraction_step2.jsonl`

如果你后续扩展了别的合金 Pipeline，只要输出仍然是 JSONL，这个查看器通常也可以直接复用。

### 10.3 典型使用流程

1. 打开 `ui/index.html`
2. 拖拽或多选导入一个或多个 `.jsonl` 文件
3. 在左侧文件列表里切换不同输出文件
4. 在左侧记录列表里选择具体样本
5. 在右侧查看摘要、元信息、结构化字段和原始 JSON

### 10.4 当前 UI 能力

- 支持本地拖拽上传和多文件导入
- 支持按标题、路径、字段内容搜索记录
- 会自动解析每行 JSON，以及记录中的 `alloy_json` 字段
- 支持复制字段内容
- 支持原始 JSON 全屏查看
- 所有解析都在浏览器本地完成，不上传文件

### 10.5 UI 使用建议

- 看整体处理进度时，优先导入 `alloy_extraction_step1.jsonl` 和 `alloy_extraction_step2.jsonl`
- 排查抽取质量时，重点对照 `source`、`text_path`、结构化字段和原始 JSON
- 如果某条记录没有正确解析 `alloy_json`，可以先从右侧原始 JSON 判断是模型输出问题还是 JSON 格式问题

更多补充说明见 [ui/README.md](/D:/XJTU/ImportantFile/auto-design-alloy/alloy_data_extraction/ui/README.md)。

## 11. 代码级示例

### 11.1 单独构建 LLM Serving

```python
from alloy_data_extraction.provider import build_api_llm_serving

llm = build_api_llm_serving(
    env_file=".env",
    max_workers=2,
    max_retries=8,
)
```

### 11.2 单独实例化 Pipeline

```python
from alloy_data_extraction.pipelines.alloy_pdf_pipeline import (
    AlloyPdfExtractionPipeline,
    resolve_resume_step,
)

pipeline = AlloyPdfExtractionPipeline(
    pdf_root=r"D:\XJTU\ImportantFile\auto-design-alloy\database\papers\arxiv",
    env_file=".env",
)
pipeline.compile()
pipeline.forward(resume_step=resolve_resume_step("./cache/alloy_pipeline"))
```

## 12. 当前实现约束

为了保持代码简单，当前版本有这些约束：

- 当前版本只抽取 4 个固定字段
- `BASE_URLS` 如果配置多个地址，只使用第一个
- Markdown 读取失败时，该条会退化为空文本抽取
- 某些 OpenAI-compatible 接口不支持 `json_schema` 时会自动降级，但仍要求模型最终返回可解析 JSON

## 13. 建议的后续扩展

如果后续继续扩展，建议保持现在这套分层：

1. 新增字段时，优先只改 `prompts/core.py` 和 `operators/domain/alloy_info_extractor.py`
2. 新增合金方向时，复用 `operators/core/markdown_json_schema_extractor.py`
3. 新增流水线步骤时，只在 `pipelines/alloy_pdf_pipeline.py` 追加算子，不把业务细节塞进 `forward()`
