from pathlib import Path
from typing import Any
import json
import mimetypes
import os
import requests, logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def convert_document(path: str | Path) -> tuple[str, dict[str, Any]]:
    path = Path(path)
    docling_url = os.environ["DOCLING_SERVE_URL"].rstrip("/")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    with open(path, "rb") as f:
        files = {
            "files": (path.name, f, mime)
        }
        form_data = {
            "to_formats": "md",
            "return_as_file": "false",
            "abort_on_error": "false",
        }

        resp = requests.post(
            f"{docling_url}/v1/convert/file",
            files=files,
            data=form_data,
            timeout=300,
        )

    if not resp.ok:
        raise RuntimeError(
            f"Docling failed: status={resp.status_code}, url={resp.url}, body={resp.text[:2000]}"
        )
    resp.raise_for_status()
    logging.info("Docling Status Code: ", resp.status_code)
    payload = resp.json()
    logging.info("Docling payload keys:", list(payload.keys()))


    document = payload.get("document", {}) or {}
    markdown = document.get("md_content", "") or ""
    structured = document.get("json_content", {}) or document
    '''
    for debugging purposes 
    print("payload keys:", list(payload.keys()), flush=True)
    print("document keys:", list(document.keys()), flush=True)
    print("status:", payload.get("status"), flush=True)
    print("errors:", payload.get("errors"), flush=True)
    print("md len:", len(markdown), flush=True)
    print("md preview:", repr(markdown[:500]), flush=True)
    print("text len:", len(document.get("text_content", "") or ""), flush=True)
    print("json_content type:", type(document.get("json_content")).__name__, flush=True)
    '''
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
    # only if script is run directly - not used by watcher
    logging.info("Wrote:")
    logging.info(md_path)
    logging.info(json_path)


if __name__ == "__main__":
    main()