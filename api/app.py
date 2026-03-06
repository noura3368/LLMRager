import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from haiku.rag.client import HaikuRAG  # adjust import if needed


APP_TOP_K = int(os.getenv("TOP_K", "6"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama:latest")

HAIKU_DB_PATH = os.getenv("HAIKU_DB_PATH", "/data/haiku.rag.lancedb")

app = FastAPI()


class QueryReq(BaseModel):
    question: str = Field(..., min_length=1)
    system_instructions: Optional[str] = None
    top_k: Optional[int] = None


def _truncate(s: str, max_chars: int) -> str:
    return s if len(s) <= max_chars else s[: max_chars - 200] + "\n\n[TRUNCATED]"


def build_prompt(question: str, context_blocks: List[Dict[str, Any]], system_instructions: Optional[str]) -> str:
    # Context is formatted with stable citation keys you can reference in the answer.
    # Each block has: id, source_path, content (and maybe page/section metadata).
    parts = []
    for i, blk in enumerate(context_blocks, start=1):
        src = blk.get("source_path") or blk.get("source") or "unknown_source"
        loc = blk.get("location") or blk.get("page") or blk.get("section") or ""
        cite = f"[S{i}]"
        header = f"{cite} {src}"
        if loc:
            header += f" ({loc})"
        text = blk.get("content", "")
        parts.append(f"{header}\n{text}")

    context_text = "\n\n---\n\n".join(parts)
    context_text = _truncate(context_text, MAX_CONTEXT_CHARS)

    base_system = (
        "You are a technical assistant. Use ONLY the provided context to answer.\n"
        "If the context is insufficient, say: 'Insufficient context in the indexed documents.'\n"
        "When you state a fact, cite the supporting source using [S#].\n"
        "Be concise and precise.\n"
    )
    if system_instructions:
        base_system += "\nAdditional instructions:\n" + system_instructions.strip() + "\n"

    user = f"Question:\n{question}\n\nContext:\n{context_text}\n\nAnswer:"
    return f"{base_system}\n\n{user}"


async def ollama_generate(prompt: str) -> str:
    # Ollama /api/generate
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Ollama error: {r.status_code} {r.text}")
        data = r.json()
        return data.get("response", "").strip()


def normalize_context_item(item: Any) -> Dict[str, Any]:
    """
    haiku.rag search/return types can vary by version.
    This tries to normalize common shapes into:
    {content, source_path, location}
    """
    if isinstance(item, dict):
        content = item.get("content") or item.get("text") or ""
        meta = item.get("metadata") or {}
        source_path = item.get("source_path") or meta.get("source") or meta.get("path") or item.get("source") or ""
        location = meta.get("page") or meta.get("section") or meta.get("location") or ""
        return {"content": content, "source_path": source_path, "location": location, "raw": item}

    # fallback: try attribute access
    content = getattr(item, "content", "") or getattr(item, "text", "")
    meta = getattr(item, "metadata", {}) or {}
    source_path = getattr(item, "source_path", "") or meta.get("source") or meta.get("path") or ""
    location = meta.get("page") or meta.get("section") or meta.get("location") or ""
    return {"content": content, "source_path": source_path, "location": location, "raw": str(item)}


@app.post("/query")
async def query(req: QueryReq):
    top_k = req.top_k or APP_TOP_K

    # Connect to haiku.rag DB and retrieve relevant chunks
    async with HaikuRAG(HAIKU_DB_PATH) as rag:
        # Depending on your haiku.rag version, this might be `search`, `retrieve`, or similar.
        # If your method name differs, change here.
        results = await rag.search(req.question, top_k=top_k)

    context_blocks = [normalize_context_item(x) for x in results]
    prompt = build_prompt(req.question, context_blocks, req.system_instructions)

    answer = await ollama_generate(prompt)

    # Provide citations as the API sees them.
    citations = []
    for i, blk in enumerate(context_blocks, start=1):
        citations.append({
            "key": f"S{i}",
            "source_path": blk.get("source_path"),
            "location": blk.get("location"),
        })

    return {
        "answer": answer,
        "citations": citations,
        "retrieved": context_blocks,  # keep for debugging; remove in production if you want
        "model": OLLAMA_MODEL,
        "top_k": top_k,
    }