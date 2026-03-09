import argparse
import inspect
from pathlib import Path

from dataflow.pipeline import PipelineABC
from dataflow.utils.storage import FileStorage

from alloy_data_extraction.operators.domain.hea_info_extractor import HEAInfoExtractor
from alloy_data_extraction.provider import build_api_llm_serving
from alloy_data_extraction.utils.manifest import build_pdf_manifest

try:
    from dataflow.operators.knowledge_cleaning import FileOrURLToMarkdownConverterLocal as MarkdownConverter
except ImportError:
    from dataflow.operators.knowledge_cleaning import FileOrURLToMarkdownConverterBatch as MarkdownConverter


DEFAULT_PDF_ROOT = r"D:\XJTU\ImportantFile\auto-design-alloy\database\papers\arxiv"
DEFAULT_CACHE_PATH = "./cache/hea_pipeline"
DEFAULT_MD_OUTPUT_DIR = "./cache/hea_pipeline/md"
DEFAULT_FILE_PREFIX = "hea_extraction"
DEFAULT_MINERU_BACKEND = "vlm-auto-engine"


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with path.open("r", encoding="utf-8", errors="ignore") as file:
        return sum(1 for _ in file)


def resolve_resume_step(cache_path: str, file_name_prefix: str = DEFAULT_FILE_PREFIX) -> int:
    """Auto-detect the resume step from cached outputs."""
    cache_dir = Path(cache_path)
    step1_path = cache_dir / f"{file_name_prefix}_step1.jsonl"
    step2_path = cache_dir / f"{file_name_prefix}_step2.jsonl"

    if step2_path.exists() and step2_path.stat().st_size > 0:
        if _count_jsonl_rows(step1_path) > _count_jsonl_rows(step2_path):
            return 1
        return 2
    if step1_path.exists() and step1_path.stat().st_size > 0:
        return 1
    return 0


def build_markdown_converter(md_output_dir: str, mineru_backend: str):
    converter_signature = inspect.signature(MarkdownConverter.__init__)
    converter_kwargs = {
        "intermediate_dir": md_output_dir,
        "mineru_backend": mineru_backend,
    }
    if "lang" in converter_signature.parameters:
        converter_kwargs["lang"] = "en"
    return MarkdownConverter(**converter_kwargs)


class HEAPdfExtractionPipeline(PipelineABC):
    def __init__(
        self,
        pdf_root: str,
        cache_path: str = DEFAULT_CACHE_PATH,
        md_output_dir: str = DEFAULT_MD_OUTPUT_DIR,
        env_file: str = ".env",
        mineru_backend: str = DEFAULT_MINERU_BACKEND,
        max_workers: int = 2,
        max_retries: int = 8,
    ):
        super().__init__()

        cache_dir = Path(cache_path)
        cache_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = build_pdf_manifest(
            pdf_root=pdf_root,
            output_jsonl=str(cache_dir / "pdf_sources.jsonl"),
        )

        self.storage = FileStorage(
            first_entry_file_name=manifest_path,
            file_name_prefix=DEFAULT_FILE_PREFIX,
            cache_path=str(cache_dir),
            cache_type="jsonl",
        )
        self.llm_serving = build_api_llm_serving(
            env_file=env_file,
            max_workers=max_workers,
            max_retries=max_retries,
        )
        self.pdf_to_markdown = build_markdown_converter(
            md_output_dir=md_output_dir,
            mineru_backend=mineru_backend,
        )
        self.extract_hea_info = HEAInfoExtractor(llm_serving=self.llm_serving)

    def forward(self):
        self.pdf_to_markdown.run(
            storage=self.storage.step(),
            input_key="source",
            output_key="text_path",
        )
        self.extract_hea_info.run(
            storage=self.storage.step(),
            input_key="text_path",
            output_key="hea_json",
        )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HEA PDF extraction pipeline with resume support.")
    parser.add_argument("--pdf-root", default=DEFAULT_PDF_ROOT, help="Root folder containing pdf files.")
    parser.add_argument("--cache-path", default=DEFAULT_CACHE_PATH)
    parser.add_argument("--md-output-dir", default=DEFAULT_MD_OUTPUT_DIR)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--mineru-backend", default=DEFAULT_MINERU_BACKEND)
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--max-retries", type=int, default=8)
    parser.add_argument(
        "--resume-step",
        default="auto",
        help="Resume step index. Use integer (0/1/2...) or 'auto' (default).",
    )
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    pipeline = HEAPdfExtractionPipeline(
        pdf_root=args.pdf_root,
        cache_path=args.cache_path,
        md_output_dir=args.md_output_dir,
        env_file=args.env_file,
        mineru_backend=args.mineru_backend,
        max_workers=args.max_workers,
        max_retries=args.max_retries,
    )
    pipeline.compile()

    if str(args.resume_step).lower() == "auto":
        resume_step = resolve_resume_step(args.cache_path, DEFAULT_FILE_PREFIX)
    else:
        resume_step = int(args.resume_step)

    pipeline.forward(resume_step=resume_step)


if __name__ == "__main__":
    main()
