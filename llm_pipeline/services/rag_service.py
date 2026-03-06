from haiku.rag.client import HaikuRAG
from pathlib import Path
import os

DB_PATH = Path(os.getenv("DB_PATH", "/data/haiku.rag.lancedb"))

async def retrieve_context(items: list[str], top_k: int = 25) -> str:
    query = " ".join(items)
    query = "I have the following commands: " + query + ". Give me many new commands that would be accepted by the same system. Please give me a python list."
    chunks = []
    async with HaikuRAG(DB_PATH, read_only=True) as client:
        results = await client.ask(query)
        
        for r in results[:top_k]:
            text = getattr(r, "text", None) or getattr(r, "content", None) or str(r)
            chunks.append(text)
    return "\n\n".join(chunks)

#async def parse_context(response): 
    