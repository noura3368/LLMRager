from pathlib import Path
from typing import Any
import json, requests, os
from docling.document_converter import DocumentConverter


_converter = DocumentConverter()


def convert_document(path: str | Path) -> tuple[str, dict[str, Any]]:
    """
    Convert a document with Docling and return:
      1. markdown export
      2. full structured JSON as a Python dict
    """
    path = Path(path)
    docling_url = os.environ["DOCLING_SERVE_URL"].rstrip("/")

    with open(path, "rb") as f:
        files = {"file": (path.name, f)}
        resp = requests.post(f"{docling_url}/convert", files=files, timeout=300)

    resp.raise_for_status()
    data = resp.json()

    markdown = data.get("markdown", "")
    structured = data.get("document", {})

    return markdown, structured


def write_debug_outputs(
    input_path: str | Path,
    out_dir: str | Path = "./docling_test",
) -> tuple[Path, Path]:
    """
    Optional debug helper:
    convert a file and write markdown/json outputs to disk.
    """
    input_path = Path(input_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    markdown, structured = convert_document(input_path)

    md_path = out_dir / f"{input_path.stem}.md"
    json_path = out_dir / f"{input_path.stem}.json"

    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(structured, indent=2, ensure_ascii=False), encoding="utf-8")

    return md_path, json_path


def main() -> None:
    pdf_path = Path("rag_server/docs/kd3005p-user-manual-3.pdf")

    md_path, json_path = write_debug_outputs(pdf_path)

    print("Wrote:", flush=True)
    print(md_path, flush=True)
    print(json_path, flush=True)


if __name__ == "__main__":
    main()