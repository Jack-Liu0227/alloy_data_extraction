import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from alloy_data_extraction.utils.manifest import build_pdf_manifest

DEFAULT_INPUT_ROOT = r"D:\XJTU\ImportantFile\auto-design-alloy\database\papers\arxiv"
DEFAULT_OUTPUT_PATH = "./cache/alloy_pipeline/pdf_sources.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build DataFlow pipeline input JSONL from local files.")
    parser.add_argument("--input-root", default=DEFAULT_INPUT_ROOT, help="Root directory containing source files.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Output JSONL file path.")
    parser.add_argument(
        "--pattern",
        default="*.pdf",
        help="Glob pattern to match source files recursively. Default: *.pdf",
    )
    args = parser.parse_args()

    output_path = build_pdf_manifest(
        pdf_root=args.input_root,
        output_jsonl=args.output,
        pattern=args.pattern,
    )
    print(f"Generated pipeline input: {output_path}")


if __name__ == "__main__":
    main()
