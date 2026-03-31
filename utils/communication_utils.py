import httpx
from fastapi import FastAPI, HTTPException

async def get_async(url, t=120):
    async with httpx.AsyncClient(timeout=t) as client:
        r = await client.get(url)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Ollama error: {r.status_code} {r.text}")
        
        data = r.json()
        return data.get("response", "").strip()
    
    
async def post_async(url, payload=None, t=120):
    async with httpx.AsyncClient(timeout=t) as client:
        r = await client.post(url, json=payload)

        if r.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Ollama error: {r.status_code} {r.text}"
            )
        data = r.json()
        return data.get("response", "").strip()
        