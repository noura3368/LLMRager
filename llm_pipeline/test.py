#!/usr/bin/env python3

import json
from pathlib import Path

from haiku.rag.client import HaikuRAG
from haiku.rag.store.models.chunk import Chunk
from haiku.rag.embeddings import embed_chunks


DB_PATH = Path("/data/haiku.rag.lancedb")
INPUT_JSON = Path("commands_extracted.json")


def record_to_chunk_text(rec: dict) -> str:
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

    return "\n".join(line for line in lines if line.strip())


def record_to_chunk(rec: dict, order: int) -> Chunk:
    return Chunk(
        content=record_to_chunk_text(rec),
        metadata={
            "entry_name": rec.get("entry_name", ""),
            "syntax": rec.get("syntax", ""),
            "command_type": rec.get("command_type", ""),
            "section_title": rec.get("section_title", ""),
        },
        order=order,
    )


async def main():
    records = json.loads(INPUT_JSON.read_text(encoding="utf-8"))

    # Build one markdown document from all entries so haiku.rag has a DoclingDocument
    manual_md_parts = []
    for rec in records:
        heading = rec.get("syntax") or rec.get("entry_name") or "Untitled"
        manual_md_parts.append(f"## {heading}\n\n{record_to_chunk_text(rec)}")

    manual_md = "\n\n".join(manual_md_parts)

    async with HaikuRAG(DB_PATH, create=True) as client:
        # Convert markdown text to a DoclingDocument
        docling_doc = await client.convert(manual_md, format="md")

        # Create one chunk per entry
        chunks = [record_to_chunk(rec, i) for i, rec in enumerate(records)]

        # Generate embeddings
        embedded_chunks = await embed_chunks(chunks)

        # Store as one document with custom chunks
        doc = await client.import_document(
            docling_document=docling_doc,
            chunks=embedded_chunks,
            uri="doc://manual/commands-extracted",
            title="Extracted Command Manual",
            metadata={"source": "llm-extracted-markdown"},
        )

        print("Imported document:", doc.id)
        print("Stored chunks:", len(embedded_chunks))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())