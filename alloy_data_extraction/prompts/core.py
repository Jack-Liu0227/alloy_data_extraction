from dataflow.core.prompt import PromptABC
from dataflow.utils.registry import PROMPT_REGISTRY


@PROMPT_REGISTRY.register()
class AlloyExtractionPrompt(PromptABC):
    """Prompt template for generic alloy literature extraction."""

    SYSTEM_PROMPT = (
        "You are a materials extraction assistant for alloy literature. "
        "Return one JSON object only. "
        "Use the exact keys category, composition, processing, UTS, YS, El, test_conditions, raw_text. "
        "Follow the requested JSON structure exactly. "
        "For missing object/string fields, return exactly 'no information'. "
        "For missing list fields, return []."
    )

    def __init__(self, max_chars: int = 50000):
        self.max_chars = max_chars
        self.system_prompt = self.SYSTEM_PROMPT

    def build_prompt(self, markdown_text: str) -> str:
        content = (markdown_text or "")[: self.max_chars]
        return (
            "Extract alloy information from the markdown below.\n\n"
            "Return exactly one JSON object with the following schema:\n\n"
            "{\n"
            '  "category": "experimental | computational | combined | no information",\n'
            '  "composition": [\n'
            '    {"element": "Fe", "value": 25, "unit": "wt%"},\n'
            '    {"element": "Co", "value": 25, "unit": "wt%"}\n'
            "  ],\n"
            '  "processing": "string or no information",\n'
            '  "UTS": {"value": 950, "unit": "MPa"},\n'
            '  "YS": {"value": 720, "unit": "MPa"},\n'
            '  "El": {"value": 32, "unit": "%"},\n'
            '  "test_conditions": [\n'
            '    {"name": "temperature", "value": 300, "unit": "K"},\n'
            '    {"name": "strain_rate", "value": 0.001, "unit": "s^-1"}\n'
            "  ],\n"
            '  "raw_text": "string or no information"\n'
            "}\n\n"
            "Field intent:\n"
            "1. category: classify the paper or main evidence as experimental, computational, combined, or no information.\n"
            "2. composition: extract element contents in structured form.\n"
            "3. processing: summarize the main processing route or computational workflow in one concise text field.\n"
            "4. UTS, YS, El: extract only these three mechanical properties.\n"
            "5. test_conditions: capture key conditions as generic name-value-unit entries.\n"
            "6. raw_text: keep a concise supporting snippet or summary from the source text that justifies the extraction.\n\n"
            "Extraction rules:\n"
            "- Prefer concrete information from title, abstract, tables, figure captions, results, and conclusion.\n"
            "- Set category to experimental, computational, combined, or no information only.\n"
            "- If multiple alloys or conditions appear, keep the main composition and main conditions concisely.\n"
            "- Use numbers for value whenever possible; do not merge value and unit into one string.\n"
            "- For composition, return [] if no reliable element-value-unit information is present.\n"
            "- For processing, keep one short text summary instead of splitting into steps.\n"
            "- For UTS, YS, and El, return {'value': 'no information', 'unit': 'no information'} when absent.\n"
            "- For test_conditions, include common items such as temperature, strain_rate, pressure, time, atmosphere, loading_mode, k_point_mesh, cutoff_energy, ensemble, or timestep when present.\n"
            "- If no key conditions are present, return [].\n"
            "- raw_text should be a short supporting excerpt or compressed evidence summary, not chain-of-thought.\n"
            "- Return exactly one JSON object and nothing else.\n"
            "- Do not output reasoning, <think>, <answer>, XML tags, or any explanatory text.\n"
            "- Do not wrap the JSON in markdown fences.\n"
            "- Missing information must follow the rules above exactly.\n\n"
            "Markdown:\n"
            f"{content}"
        )
