# server - client FASTAPI method not working yet 
# assume an arbritary list of commands 
import datetime, csv, sys
from collections import defaultdict
import os, requests
from pathlib import Path
from fastapi import FastAPI
from urllib.parse import urlparse, parse_qs, unquote
import re
from services.run import main
from services.rag_service import retrieve_context

app = FastAPI()

def extract_items_from_url(url: str) -> list[str]:
    parsed = urlparse(url)

    query = parse_qs(parsed.query)
    if "items" in query:
        raw = query["items"][0]
        return [x.strip() for x in raw.split(",") if x.strip()]

    path_parts = [p for p in parsed.path.split("/") if p]
    if not path_parts:
        return []

    last = unquote(path_parts[-1])

    m = re.match(r"^\[(.*)\]$", last)
    if m:
        return [x.strip() for x in m.group(1).split(",") if x.strip()]

    return [last] if last else []

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/generate")
async def generate(payload: dict):
    api_url = payload.get("api_url", "")
    items = extract_items_from_url(api_url)
    rag_output = await retrieve_context(items)  
    main(items, rag_output) 
    return {
        "api_url": api_url,
        "extracted_items": items,
        "next_step": rag_output # This will be an awaitable, handle accordingly in real implementation
    }
