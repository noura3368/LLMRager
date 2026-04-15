#!/usr/bin/env python3

import asyncio
import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any
import re
import subprocess
from pypdf import PdfReader
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from services.create_markdown import convert_document, write_debug_outputs
from services.read_markdown import main_func
import logging 
from haiku.rag.client import HaikuRAG

RAW_DIR = Path(os.getenv("RAW_DIR", "/raw_docs"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", "/docs_processed"))
DB_PATH = Path(os.getenv("DB_PATH", "/data/haiku.rag.lancedb"))
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


def read_preview(path: Path, max_chars: int = 4000) -> str:
    try:
        if path.suffix.lower() == ".pdf":
            reader = PdfReader(str(path))
            pieces = []
            for page in reader.pages[:2]:
                pieces.append(page.extract_text() or "")
            return "\n".join(pieces)[:max_chars]

        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""


def is_instruction_manual(path: Path) -> bool:
    name = path.name.lower()

    if any(k in name for k in MANUAL_NAME_KEYWORDS) and name.endswith((".pdf")):
        return True

    preview = read_preview(path).lower()
    hits = sum(1 for k in MANUAL_TEXT_KEYWORDS if k in preview)
    return hits >= 3 and name.endswith((".pdf"))


def preprocess_manual(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    markdown, _ = convert_document(path)
    logging.info(f"Preprocessed file.")
    records, plain_sections = main_func(markdown, watcher_call=True)
    logging.info(f"Extracted {len(records)} command records and {len(plain_sections)} plain text sections")
    return records, plain_sections


_INLINE_IMAGE_RE = re.compile(r"!\[.*?\]\(data:image/[^)]*\)")


def save_plain_sections_as_markdown(plain_sections: list[str], source_path: Path) -> Path | None:
    """Write non-command sections to PROCESSED_DIR as a .md file for haiku-monitor to chunk."""
    content = "\n\n".join(s for s in plain_sections if s.strip())
    content = _INLINE_IMAGE_RE.sub("", content)
    if not content.strip():
        return None
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    md_path = PROCESSED_DIR / f"{source_path.stem}.md"
    md_path.write_text(content, encoding="utf-8")
    logging.info(f"[manual] plain sections saved -> {md_path}")
    return md_path


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
        param_text = "; ".join(f"{k} = {v}" for k, v in params.items())
        lines.append(f"Parameters: {param_text}")

    notes = rec.get("notes", [])
    if notes:
        lines.append("Notes: " + " | ".join(str(x) for x in notes))

    examples = rec.get("examples", [])
    if examples:
        lines.append("Examples: " + " | ".join(str(x) for x in examples))

    neighbours = rec.get("neighbours", [])
    if neighbours:
        neighbour_text = ", ".join(
            n.get("syntax", "") or n.get("entry_name", "")
            for n in neighbours
            if isinstance(n, dict)
        )
        if neighbour_text:
            lines.append(f"Neighbours: {neighbour_text}")

    lines.append(f"Section Title: {rec.get('section_title', '')}")

    return "\n".join(x for x in lines if x.strip())


async def import_manual_records(records: list[dict[str, Any]], source_path: Path, file_hash: str) -> list[str]:
    document_ids = []
    async with HaikuRAG(DB_PATH, create=True) as client:
        for i, rec in enumerate(records):
            text = record_to_text(rec)
            title = rec.get("syntax") or rec.get("entry_name") or f"{source_path.stem}-{i}"
            uri = f"manual://{source_path.name}#{i}"

            doc = await client.create_document(
                text,
                title=title,
                uri=uri,
                metadata={
                    "source_type": "instruction_manual",
                    "source_raw_path": str(source_path),
                    "source_raw_file": source_path.name,
                    "source_file_hash": file_hash,
                    "entry_index": i,
                    "entry_name": rec.get("entry_name", ""),
                    "syntax": rec.get("syntax", ""),
                    "section_title": rec.get("section_title", ""),
                },
            )
            document_ids.append(str(doc.id))
    return document_ids


def process_non_manual(path: Path) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dst = PROCESSED_DIR / path.name
    shutil.copy2(path, dst)
    logging.info(f"[normal] copied {path} -> {dst}")


def process_manual(path: Path, file_hash: str, state: dict) -> None:
    records, plain_sections = preprocess_manual(path)

    document_ids = asyncio.run(import_manual_records(records, path, file_hash))

    plain_md = save_plain_sections_as_markdown(plain_sections, path)

    state["files"][str(path)] = {
        "sha256": file_hash,
        "kind": "manual",
        "document_ids": document_ids,
        "plain_md_path": str(plain_md) if plain_md else None,
        "processed_at": time.time(),
    }
    save_state(state)
    logging.info(f"[manual] imported {len(records)} command records + plain text -> {plain_md} from {path.name}")


def handle_file(path: Path, state: dict[str, Any]) -> None:
    if not path.exists() or not path.is_file():
        return

    if path.suffix.lower() not in SUPPORTED_EXTS:
        logging.warning(f"[skip] unsupported extension: {path.name}")
        return

    file_hash = sha256_file(path)
    old_hash = state["files"].get(str(path), {}).get("sha256")

    if old_hash == file_hash:
        logging.info(f"[skip] unchanged: {path.name}")
        return

    if is_instruction_manual(path):
        process_manual(path, file_hash, state)
        #kind = "manual"
    else:
        process_non_manual(path)
        state["files"][str(path)] = {
            "sha256": file_hash,
            "kind": "normal",
            "processed_at": time.time(),
        }
        save_state(state)

def delete_manual_documents(document_ids: list[str]) -> None:
    for doc_id in document_ids:
        try:
            subprocess.run(
                [
                    "haiku-rag",
                    "--config", "/app/haiku.rag.yaml",
                    "delete",
                    doc_id,
                    "--db", "/data/haiku.rag.lancedb",
                ],
                check=True,
            )
            logging.info(f"[delete] removed manual doc {doc_id}")
        except Exception as e:
            logging.error(f"[delete] failed for {doc_id}: {e}")

class Handler(FileSystemEventHandler):
    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        time.sleep(1)
        handle_file(path, self.state)

    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        time.sleep(1)
        handle_file(path, self.state)

    def on_deleted(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        info = self.state["files"].pop(str(path), None)
        save_state(self.state)
        if not info:
            logging.warning(f"[delete] no state for {path}")
            return
        
        if info and info.get("kind") == "normal":
            processed = PROCESSED_DIR / path.name
            if processed.exists():
                processed.unlink()
                logging.info(f"[delete] removed processed file {processed}")

        # delete command records from RAG, then remove the plain-text .md so
        # haiku-monitor's delete_orphans cleans up its chunks automatically
        elif info.get("kind") == "manual":
            doc_ids = info.get("document_ids", [])
            delete_manual_documents(doc_ids)

            plain_md = info.get("plain_md_path")
            if plain_md:
                plain_md_path = Path(plain_md)
                if plain_md_path.exists():
                    plain_md_path.unlink()
                    logging.info(f"[delete] removed plain markdown {plain_md_path}")

            logging.info(f"[delete] raw file removed: {path}")



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