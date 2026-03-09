# Alloy Data Extraction

English documentation for this project. The default documentation remains Chinese in [README.md](/D:/XJTU/ImportantFile/auto-design-alloy/alloy_data_extraction/README.md).

## Overview

This project extracts structured HEA information from academic PDFs with a DataFlow pipeline:

1. Convert PDF files to Markdown
2. Extract structured alloy information from Markdown with an LLM

Current output fields:

- `composition`
- `processing`
- `properties`
- `test_conditions`

Missing fields are filled with `"no information"`.

## Project Layout

```text
alloy_data_extraction/
├─ alloy_data_extraction/
│  ├─ provider.py
│  ├─ operators/
│  ├─ pipelines/
│  ├─ prompts/
│  └─ utils/
├─ scripts/
├─ .env.example
├─ requirements.txt
├─ README.md
└─ README_EN.md
```

## Setup

Use Python 3.10+ and install dependencies:

```bash
pip install -r requirements.txt
```

Core dependency:

- `open-dataflow`

## LLM Configuration

The current codebase reads one unified LLM env group from `.env`. The entry point is [provider.py](/D:/XJTU/ImportantFile/auto-design-alloy/alloy_data_extraction/alloy_data_extraction/provider.py).

Required variables:

- `DF_API_KEY`
- `DF_MODEL_ID`
- `DF_BASE_URL` or `DF_BASE_URLS`

Notes:

- `DF_BASE_URL` is the recommended form
- If `DF_BASE_URLS` contains multiple URLs, only the first one is used
- If the configured URL does not end with `/v1/chat/completions`, the code appends the OpenAI-compatible path automatically

### Quick Start

Copy the template:

```bash
copy .env.example .env
```

Fill one model configuration only.

Example:

```env
DF_API_KEY=your_api_key
DF_BASE_URL=https://api.deepseek.com/v1
DF_MODEL_ID=deepseek-chat
```

To switch providers or models, update these three values only.

## Running the Pipeline

Default run:

```bash
python -m alloy_data_extraction.pipelines.hea_pdf_pipeline \
  --pdf-root "D:\XJTU\ImportantFile\auto-design-alloy\database\papers\arxiv" \
  --cache-path "./cache/hea_pipeline" \
  --md-output-dir "./cache/hea_pipeline/md" \
  --env-file ".env" \
  --resume-step auto
```

## Resume Logic

Resume logic is implemented in [hea_pdf_pipeline.py](/D:/XJTU/ImportantFile/auto-design-alloy/alloy_data_extraction/alloy_data_extraction/pipelines/hea_pdf_pipeline.py).

- `step1`: PDF -> Markdown
- `step2`: Markdown -> HEA extraction

Manual resume example:

```bash
python -m alloy_data_extraction.pipelines.hea_pdf_pipeline --resume-step 1
```

## Outputs

Default cache directory:

```text
./cache/hea_pipeline
```

Main outputs:

- `pdf_sources.jsonl`
- `hea_extraction_step1.jsonl`
- `hea_extraction_step2.jsonl`
- `md/`

Final extracted columns:

- `hea_json`
- `composition`
- `processing`
- `properties`
- `test_conditions`

## Constraints

- Only 4 fixed fields are extracted right now
- If multiple URLs are configured in `BASE_URLS`, only the first one is used
- If Markdown reading fails, extraction falls back to empty text
- If an OpenAI-compatible endpoint does not support `json_schema`, the pipeline falls back to plain-text response parsing, but the model must still return valid JSON
