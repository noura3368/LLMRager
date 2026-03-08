from haiku.rag.client import HaikuRAG
from pathlib import Path
import os

DB_PATH = Path(os.getenv("DB_PATH", "/data/haiku.rag.lancedb"))

async def retrieve_context(items: list[str], top_k: int = 5) -> str:
    query = " ".join(items)
    query = "These are  valid commands for a target: " + query + " \
            Retrieve information and documentation for additional commands that the target would accept"
    chunks = []
    async with HaikuRAG(DB_PATH, read_only=True) as client:
        results = await client.search(query)
        
        for r in results[:top_k]:
            text = getattr(r, "text", None) or getattr(r, "content", None) or str(r)
            chunks.append(text)
            print("chunks", r)
    return "\n\n".join(chunks)

#async def parse_context(response): 
    