from pathlib import Path

import pandas as pd


def build_pdf_manifest(pdf_root: str, output_jsonl: str, pattern: str = "*.pdf") -> str:
    root = Path(pdf_root)
    if not root.exists():
        raise FileNotFoundError(f"Input directory does not exist: {pdf_root}")

    files = sorted(str(path.resolve()) for path in root.rglob(pattern))
    dataframe = pd.DataFrame({"source": files})

    output_path = Path(output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_json(output_path, orient="records", lines=True, force_ascii=False)
    return str(output_path)
