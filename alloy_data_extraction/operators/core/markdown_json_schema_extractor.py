import json
import re
import time
from pathlib import Path
from copy import deepcopy
from typing import Any, Mapping, Sequence

from dataflow import get_logger
from dataflow.core import LLMServingABC, OperatorABC
from dataflow.utils.storage import DataFlowStorage


class MarkdownJsonSchemaExtractor(OperatorABC):
    """Read markdown files from a DataFrame column and extract structured JSON."""

    def __init__(
        self,
        llm_serving: LLMServingABC,
        prompt_template,
        json_schema: Mapping[str, object],
        default_record: Mapping[str, object],
        max_chars: int = 50000,
        request_retries: int = 3,
        retry_sleep_sec: float = 2.0,
        save_every: int = 5,
        keep_raw_output: bool = True,
        raw_output_key: str = "llm_raw_output",
    ):
        self.logger = get_logger()
        self.llm_serving = llm_serving
        self.prompt_template = prompt_template
        self.json_schema = dict(json_schema)
        self.default_record = dict(default_record)
        self.max_chars = max_chars
        self.request_retries = request_retries
        self.retry_sleep_sec = retry_sleep_sec
        self.save_every = max(1, int(save_every))
        self.keep_raw_output = keep_raw_output
        self.raw_output_key = raw_output_key

    @staticmethod
    def get_desc(lang: str = "zh"):
        if lang == "zh":
            return (
                "MarkdownJsonSchemaExtractor 用于读取 DataFrame 指定列中的 Markdown 文件路径，"
                "调用 LLM 按给定 Prompt 和 JSON Schema 提取结构化字段，并把结果写回数据表。"
            )
        if lang == "en":
            return (
                "MarkdownJsonSchemaExtractor reads markdown file paths from a DataFrame column, "
                "uses an LLM with a prompt template and JSON schema, and writes structured fields back."
            )
        return "Extract structured JSON from markdown files."

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json|JSON)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    @classmethod
    def _extract_json_candidate(cls, raw_text: str) -> str:
        text = cls._strip_code_fence(raw_text)
        text = re.sub(r"^\s*(?:json|JSON)\s*", "", text).strip()

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]
        return text

    @staticmethod
    def _iter_json_objects(text: str):
        start = -1
        depth = 0
        in_string = False
        escape = False

        for index, char in enumerate(text):
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue

            if char == "{":
                if depth == 0:
                    start = index
                depth += 1
            elif char == "}":
                if depth == 0:
                    continue
                depth -= 1
                if depth == 0 and start != -1:
                    yield text[start : index + 1]
                    start = -1

    @staticmethod
    def _is_missing_scalar(value: Any) -> bool:
        return value is None or (isinstance(value, str) and not value.strip())

    @classmethod
    def _merge_with_default(cls, default_value: Any, parsed_value: Any) -> Any:
        if isinstance(default_value, dict):
            if not isinstance(parsed_value, dict):
                return deepcopy(default_value)
            merged: dict[str, Any] = {}
            for key, value in default_value.items():
                merged[key] = cls._merge_with_default(value, parsed_value.get(key))
            return merged

        if isinstance(default_value, list):
            if not isinstance(parsed_value, list):
                return []
            return parsed_value

        if cls._is_missing_scalar(parsed_value):
            return deepcopy(default_value)
        return parsed_value

    def _parse_candidate_to_record(self, candidate: str) -> dict | None:
        try:
            parsed = json.loads(candidate)
        except Exception:
            return None
        if not isinstance(parsed, dict):
            return None

        record = deepcopy(self.default_record)
        matched = False
        for key, default_value in self.default_record.items():
            if key not in parsed:
                continue
            record[key] = self._merge_with_default(default_value, parsed.get(key))
            matched = True
        return record if matched else None

    def _extract_candidate_texts(self, raw_text: str) -> list[str]:
        if not raw_text:
            return []

        candidates: list[str] = []

        stripped = raw_text.strip()
        if stripped:
            candidates.append(stripped)
            candidates.append(self._extract_json_candidate(stripped))

        for pattern in (
            r"<answer>\s*(.*?)\s*</answer>",
            r"<final_answer>\s*(.*?)\s*</final_answer>",
            r"```json\s*(.*?)\s*```",
            r"```\s*(.*?)\s*```",
        ):
            matches = re.findall(pattern, raw_text, flags=re.IGNORECASE | re.DOTALL)
            for match in matches:
                cleaned = match.strip()
                if cleaned:
                    candidates.append(cleaned)
                    candidates.append(self._extract_json_candidate(cleaned))

        for candidate in list(candidates):
            for json_object in self._iter_json_objects(candidate):
                candidates.append(json_object)

        deduplicated: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            normalized = candidate.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduplicated.append(normalized)
        return deduplicated

    def _normalize_record(self, raw_text: str) -> dict:
        record = deepcopy(self.default_record)
        if not raw_text:
            return record

        for candidate in self._extract_candidate_texts(raw_text):
            parsed_record = self._parse_candidate_to_record(candidate)
            if parsed_record is not None:
                return parsed_record

        preview = raw_text[:300].replace("\n", "\\n")
        self.logger.warning(f"Failed to parse LLM output as JSON object, fallback to defaults: {preview}")
        return record

    @staticmethod
    def _resolve_markdown_path(raw_path: str) -> Path | None:
        if not raw_path:
            return None

        path = Path(raw_path)
        candidates = [path]
        if not path.is_absolute():
            candidates.append(Path.cwd() / path)

        for candidate in candidates:
            if candidate.exists():
                return candidate

        for candidate in candidates:
            alias_fixed = Path(str(candidate).replace("vlm-auto-engine", "vlm"))
            if alias_fixed.exists():
                return alias_fixed

        if not path.name:
            return None

        for candidate in Path.cwd().glob(f"**/{path.name}"):
            if candidate.is_file():
                return candidate
        return None

    def _read_markdown(self, markdown_path: str) -> str:
        resolved = self._resolve_markdown_path(markdown_path)
        if resolved is None or not resolved.exists():
            self.logger.warning(f"Markdown path not found: {markdown_path}")
            return ""

        try:
            return resolved.read_text(encoding="utf-8", errors="ignore")[: self.max_chars]
        except Exception as exc:
            self.logger.warning(f"Failed to read markdown file {resolved}: {exc}")
            return ""

    def _safe_generate_one(self, prompt: str, row_index: int) -> str:
        last_error = None
        schema_enabled = bool(getattr(self.llm_serving, "supports_json_schema", True))
        system_prompt = getattr(self.prompt_template, "system_prompt", None)

        for attempt in range(1, self.request_retries + 1):
            try:
                request_kwargs = {
                    "user_inputs": [prompt],
                    "system_prompt": system_prompt,
                }
                if schema_enabled:
                    request_kwargs["json_schema"] = self.json_schema
                response = self.llm_serving.generate_from_input(**request_kwargs)
                text = response[0] if response else ""
                if isinstance(text, str) and text.strip():
                    return text
                raise ValueError("LLM returned empty response")
            except Exception as exc:
                last_error = exc
                error_text = str(exc).lower()
                if schema_enabled and any(
                    marker in error_text
                    for marker in (
                        "response_format type is unavailable",
                        "response_format",
                        "json_schema",
                        "json schema",
                    )
                ):
                    schema_enabled = False
                    self.logger.warning(
                        f"Provider does not support json_schema for row={row_index}; fallback to plain text mode."
                    )
                    continue
                self.logger.warning(
                    f"LLM request failed for row={row_index}, attempt={attempt}/{self.request_retries}: {exc}"
                )
                if attempt < self.request_retries:
                    time.sleep(self.retry_sleep_sec * attempt)

        self.logger.error(f"LLM request permanently failed for row={row_index}: {last_error}")
        return ""

    def _ensure_output_columns(self, dataframe, output_key: str, output_fields: Sequence[str]) -> None:
        columns = [output_key, *output_fields]
        if self.keep_raw_output:
            columns.append(self.raw_output_key)
        for column in columns:
            if column not in dataframe.columns:
                dataframe[column] = ""

    def run(
        self,
        storage: DataFlowStorage,
        input_key: str = "text_path",
        output_key: str = "structured_json",
    ):
        dataframe = storage.read("dataframe")
        self._ensure_output_columns(dataframe, output_key, tuple(self.default_record.keys()))

        total = len(dataframe)
        for position, (row_index, row) in enumerate(dataframe.iterrows(), start=1):
            markdown_path = str(row.get(input_key, "") or "").strip()
            markdown_text = self._read_markdown(markdown_path)
            prompt = self.prompt_template.build_prompt(markdown_text=markdown_text)
            raw_output = self._safe_generate_one(prompt=prompt, row_index=int(row_index))
            record = self._normalize_record(raw_output)

            if self.keep_raw_output:
                dataframe.at[row_index, self.raw_output_key] = raw_output
            dataframe.at[row_index, output_key] = json.dumps(record, ensure_ascii=False)
            for field_name, field_value in record.items():
                dataframe.at[row_index, field_name] = field_value

            if position % self.save_every == 0:
                storage.write(dataframe)
                self.logger.info(f"Checkpoint saved: {position}/{total}")

        storage.write(dataframe)
        return output_key
