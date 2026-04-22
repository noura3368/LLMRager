#!/usr/bin/env python3

import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any
from pypdf import PdfReader
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from services.create_markdown import convert_document
from services.read_markdown import main_func
import logging

RAW_DIR = Path(os.getenv("RAW_DIR", "/raw_docs"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", "/docs_processed"))
STATE_PATH = Path(os.getenv("STATE_PATH", "/data/watcher_state.json"))

SUPPORTED_EXTS = {".pdf", ".txt", ".md", ".json", ".html", ".csv"}

MANUAL_NAME_KEYWORDS = {
    "manual", "instruction", "user_guide", "user-guide",
    "programming", "command", "reference", "protocol",
    "datasheet", "instruction set", "instruction_set"
}

MANUAL_TEXT_KEYWORDS = {
    "syntax", "parameters", "parameter", "example",
    "description", "response", "command", "commands",
    "usage", "returns", "query"
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"files": {}}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Instruction manual detection
# ---------------------------------------------------------------------------

def read_preview(path: Path, max_chars: int = 4000) -> str:
    try:
        reader = PdfReader(str(path))
        pieces = [page.extract_text() or "" for page in reader.pages[:2]]
        return "\n".join(pieces)[:max_chars]
    except Exception:
        return ""


def is_instruction_manual(path: Path) -> bool:
    name = path.name.lower()
    if any(k in name for k in MANUAL_NAME_KEYWORDS):
        return True
    preview = read_preview(path).lower()
    return sum(1 for k in MANUAL_TEXT_KEYWORDS if k in preview) >= 3


# ---------------------------------------------------------------------------
# PDF content inspection
# ---------------------------------------------------------------------------

def pdf_has_tables_or_images(path: Path) -> bool:
    """Return True if the PDF contains any images or table-like content."""
    try:
        reader = PdfReader(str(path))
        for page in reader.pages:
            # Images embedded in the page
            if page.images:
                return True

            text = page.extract_text() or ""
            lines = [l for l in text.splitlines() if l.strip()]

            # ASCII / markdown-style table rows  (at least 2 pipe characters)
            if sum(1 for l in lines if l.count("|") >= 2) >= 2:
                return True

            # Tab-separated columns  (multiple tabs on multiple lines)
            if sum(1 for l in lines if l.count("\t") >= 2) >= 3:
                return True

    except Exception as e:
        logging.warning(f"[inspect] could not inspect {path.name}: {e}")

    return False


# ---------------------------------------------------------------------------
# Processing paths
# ---------------------------------------------------------------------------

# Strips all markdown image syntax: ![alt](src)
_IMAGE_RE = re.compile(r"!\[.*?\]\([^)]*\)")


def record_to_text(rec: dict[str, Any]) -> str:
    lines = [
        f"Entry Name: {rec.get('entry_name', '')}",
        f"Command Syntax: {rec.get('syntax', '')}",
        f"Command Type: {rec.get('command_type', '')}",
        f"Description: {rec.get('description', '')}",
        f"Response: {rec.get('response', '')}",
    ]
    params = rec.get("parameters", {})
    if isinstance(params, dict) and params:
        lines.append("Parameters: " + "; ".join(f"{k} = {v}" for k, v in params.items()))
    if rec.get("notes"):
        lines.append("Notes: " + " | ".join(str(x) for x in rec["notes"]))
    if rec.get("examples"):
        lines.append("Examples: " + " | ".join(str(x) for x in rec["examples"]))
    neighbours = rec.get("neighbours", [])
    if neighbours:
        neighbour_text = ", ".join(
            n.get("syntax", "") or n.get("entry_name", "")
            for n in neighbours if isinstance(n, dict)
        )
        if neighbour_text:
            lines.append(f"Neighbours: {neighbour_text}")
    lines.append(f"Section Title: {rec.get('section_title', '')}")
    return "\n".join(x for x in lines if x.strip())


def process_complex_pdf(path: Path, file_hash: str, state: dict[str, Any]) -> None:
    """Docling → LLM extraction → one .md file per command record in
    PROCESSED_DIR so haiku-monitor ingests each record as a single atomic
    chunk. Plain (non-command) sections go into one combined .md file."""
    markdown, _ = convert_document(path)
    logging.info(f"[complex] Docling conversion done for {path.name}")

    records, plain_sections = main_func(markdown, watcher_call=True)
    logging.info(f"[complex] extracted {len(records)} command records, {len(plain_sections)} plain sections")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Each command record gets its own file so the chunker cannot split it.
    # A markdown heading is prepended so docling-serve treats it as a valid
    # document (avoids "document.json failed to convert" warning).
    record_md_paths: list[str] = []
    for i, rec in enumerate(records):
        body = record_to_text(rec)
        if not body.strip():
            continue
        heading = rec.get("syntax") or rec.get("entry_name") or f"{path.stem}-{i}"
        content = f"### {heading}\n\n{body}"
        rec_path = PROCESSED_DIR / f"{path.stem}_cmd_{i:04d}.md"
        rec_path.write_text(content, encoding="utf-8")
        record_md_paths.append(str(rec_path))
    logging.info(f"[complex] wrote {len(record_md_paths)} command record files")

    # Plain sections (no commands found) go into a single combined file.
    plain_md_path = None
    plain_content = _IMAGE_RE.sub("", "\n\n".join(s for s in plain_sections if s.strip()))
    if plain_content.strip():
        plain_md = PROCESSED_DIR / f"{path.stem}_plain.md"
        plain_md.write_text(plain_content, encoding="utf-8")
        plain_md_path = str(plain_md)
        logging.info(f"[complex] plain sections saved -> {plain_md}")

    state["files"][str(path)] = {
        "sha256": file_hash,
        "kind": "complex_pdf",
        "record_md_paths": record_md_paths,
        "plain_md_path": plain_md_path,
        "processed_at": time.time(),
    }
    save_state(state)
    logging.info(f"[complex] done: {len(record_md_paths)} record files + plain -> {plain_md_path}")


def process_simple_pdf(path: Path, file_hash: str, state: dict[str, Any]) -> None:
    """Copy a plain PDF straight to PROCESSED_DIR; haiku RAG handles chunking."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dst = PROCESSED_DIR / path.name
    shutil.copy2(path, dst)
    logging.info(f"[simple] copied {path.name} -> {dst}")

    state["files"][str(path)] = {
        "sha256": file_hash,
        "kind": "simple_pdf",
        "processed_at": time.time(),
    }
    save_state(state)


def process_other(path: Path, file_hash: str, state: dict[str, Any]) -> None:
    """Copy non-PDF files straight to PROCESSED_DIR."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dst = PROCESSED_DIR / path.name
    shutil.copy2(path, dst)
    logging.info(f"[other] copied {path.name} -> {dst}")

    state["files"][str(path)] = {
        "sha256": file_hash,
        "kind": "other",
        "processed_at": time.time(),
    }
    save_state(state)


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def handle_file(path: Path, state: dict[str, Any]) -> None:
    if not path.exists() or not path.is_file():
        return

    if path.suffix.lower() not in SUPPORTED_EXTS:
        logging.warning(f"[skip] unsupported extension: {path.name}")
        return

    file_hash = sha256_file(path)
    if state["files"].get(str(path), {}).get("sha256") == file_hash:
        logging.info(f"[skip] unchanged: {path.name}")
        return

    if path.suffix.lower() == ".pdf" and is_instruction_manual(path):
        logging.info(f"[route] instruction manual: {path.name}")
        process_complex_pdf(path, file_hash, state)
    else:
        process_other(path, file_hash, state)


# ---------------------------------------------------------------------------
# Watchdog handler
# ---------------------------------------------------------------------------

class Handler(FileSystemEventHandler):
    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state

    def on_created(self, event):
        if event.is_directory:
            return
        time.sleep(1)
        handle_file(Path(event.src_path), self.state)

    def on_modified(self, event):
        if event.is_directory:
            return
        time.sleep(1)
        handle_file(Path(event.src_path), self.state)

    def on_deleted(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        info = self.state["files"].pop(str(path), None)
        save_state(self.state)

        if not info:
            logging.warning(f"[delete] no state for {path}")
            return

        kind = info.get("kind")

        if kind == "complex_pdf":
            # Remove per-record files
            for rp in info.get("record_md_paths", []):
                p = Path(rp)
                if p.exists():
                    p.unlink()
                    logging.info(f"[delete] removed record file {p}")
            # Remove plain-sections file
            plain_md = info.get("plain_md_path") or info.get("processed_md_path")
            if plain_md:
                p = Path(plain_md)
                if p.exists():
                    p.unlink()
                    logging.info(f"[delete] removed plain markdown {p}")

        elif kind in ("simple_pdf", "other"):
            processed = PROCESSED_DIR / path.name
            if processed.exists():
                processed.unlink()
                logging.info(f"[delete] removed processed file {processed}")

        logging.info(f"[delete] handled removal of {path.name} (kind={kind})")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def initial_scan(state: dict[str, Any]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for path in RAW_DIR.rglob("*"):
        if path.is_file():
            handle_file(path, state)


def main() -> None:
    state = load_state()
    initial_scan(state)

    observer = Observer()
    observer.schedule(Handler(state), str(RAW_DIR), recursive=True)
    observer.start()
    logging.info(f"Watching {RAW_DIR}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
