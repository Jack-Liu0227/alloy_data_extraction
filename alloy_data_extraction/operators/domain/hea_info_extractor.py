from typing import Union

from dataflow.core import LLMServingABC
from dataflow.core.prompt import DIYPromptABC, prompt_restrict
from dataflow.utils.registry import OPERATOR_REGISTRY

from alloy_data_extraction.operators.core.markdown_json_schema_extractor import (
    MarkdownJsonSchemaExtractor,
)
from alloy_data_extraction.prompts.core import HEAExtractionPrompt


HEA_DEFAULT_RECORD = {
    "category": "no information",
    "composition": [],
    "processing": "no information",
    "UTS": {"value": "no information", "unit": "no information"},
    "YS": {"value": "no information", "unit": "no information"},
    "El": {"value": "no information", "unit": "no information"},
    "test_conditions": [],
    "raw_text": "no information",
}

HEA_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "composition": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "element": {"type": "string"},
                    "value": {"type": ["number", "string"]},
                    "unit": {"type": "string"},
                },
                "required": ["element", "value", "unit"],
                "additionalProperties": False,
            },
        },
        "processing": {"type": "string"},
        "UTS": {
            "type": "object",
            "properties": {
                "value": {"type": ["number", "string"]},
                "unit": {"type": "string"},
            },
            "required": ["value", "unit"],
            "additionalProperties": False,
        },
        "YS": {
            "type": "object",
            "properties": {
                "value": {"type": ["number", "string"]},
                "unit": {"type": "string"},
            },
            "required": ["value", "unit"],
            "additionalProperties": False,
        },
        "El": {
            "type": "object",
            "properties": {
                "value": {"type": ["number", "string"]},
                "unit": {"type": "string"},
            },
            "required": ["value", "unit"],
            "additionalProperties": False,
        },
        "test_conditions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": ["number", "string"]},
                    "unit": {"type": "string"},
                },
                "required": ["name", "value", "unit"],
                "additionalProperties": False,
            },
        },
        "category": {"type": "string"},
        "raw_text": {"type": "string"},
    },
    "required": ["category", "composition", "processing", "UTS", "YS", "El", "test_conditions", "raw_text"],
    "additionalProperties": False,
}


@prompt_restrict(HEAExtractionPrompt)
@OPERATOR_REGISTRY.register()
class HEAInfoExtractor(MarkdownJsonSchemaExtractor):
    """HEA-specific wrapper around the generic markdown JSON extractor."""

    def __init__(
        self,
        llm_serving: LLMServingABC,
        prompt_template: Union[HEAExtractionPrompt, DIYPromptABC, None] = None,
        max_chars: int = 50000,
        request_retries: int = 3,
        retry_sleep_sec: float = 2.0,
        save_every: int = 5,
    ):
        super().__init__(
            llm_serving=llm_serving,
            prompt_template=prompt_template or HEAExtractionPrompt(max_chars=max_chars),
            json_schema=HEA_JSON_SCHEMA,
            default_record=HEA_DEFAULT_RECORD,
            max_chars=max_chars,
            request_retries=request_retries,
            retry_sleep_sec=retry_sleep_sec,
            save_every=save_every,
        )

    @staticmethod
    def get_desc(lang: str = "zh"):
        if lang == "zh":
            return (
                "HEAInfoExtractor 是高熵合金文献抽取算子。"
                "它读取 Markdown 内容路径，输出 hea_json 以及 composition、processing、properties、test_conditions 四列。"
            )
        if lang == "en":
            return (
                "HEAInfoExtractor extracts HEA-specific fields from markdown paths and writes "
                "hea_json, category, composition, processing, UTS, YS, El, and test_conditions."
            )
        return "Extract HEA-specific fields from markdown."

    def run(
        self,
        storage,
        input_key: str = "text_path",
        output_key: str = "hea_json",
    ):
        return super().run(storage=storage, input_key=input_key, output_key=output_key)
