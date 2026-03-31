from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from services.rag_service import retrieve_context
from services.run import main_func
from utils.communication_utils import get_async, post_async
import os

app = FastAPI()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

class GenerateRequest(BaseModel):
    items: list[str] = Field(..., min_length=1)
    number_of_commands: int = Field(..., ge=1)

class SetModelRequest(BaseModel):
    model: str


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/generate")
async def generate(payload: GenerateRequest):
    items = [x.strip() for x in payload.items if x.strip()]
    number_of_commands = payload.number_of_commands

    if not items:
        raise HTTPException(status_code=400, detail="items must contain at least one non-empty value")

    rag_output = await retrieve_context(items)

    main_output = await run_in_threadpool(
        main_func,
        items,
        rag_output,
        number_of_commands,
        type="generate",
    )

    return {
        "results": main_output,
    }

@app.post("/modify")
async def modify(payload: GenerateRequest):
    items = [x.strip() for x in payload.items if x.strip()]
    number_of_commands = payload.number_of_commands

    if not items:
        raise HTTPException(status_code=400, detail="items must contain at least one non-empty value")

    rag_output = await retrieve_context(items)

    main_output = await run_in_threadpool(
        main_func,
        items,
        rag_output,
        number_of_commands,
        type="modify",
    )

    return {
        "results": main_output,
    }
    
@app.get("/list")
async def list_models():
    """
    Return a list of currently downloaded models
    """
    
    current_running_model = f"{OLLAMA_URL}/api/ps"
    all_models = f"{OLLAMA_URL}/api/tags"
    
    curr_resp = await get_async(current_running_model, 140)
    all_resp = await get_async(all_models, 140)
    
    # TODO: Return a list of the models
    
    return {"running_model": "model", "all_models": ["m1", "m2"]}


@app.post("/set_model")
async def list_models(payload: SetModelRequest):
    """ First pull the model if its not downloaded
        Then set the env vars to used the pulled model
    """
    
    url = f"{OLLAMA_URL}/api/pull"
    body = { "model": payload.model }

    response = await post_async(url, body, 140)
    
    return {
        "model": payload.model
    }


@app.get("/download_status")
async def download_status():
    """ 
        Makes a get requst for the ollama logs
        Then parses the logs fopr 
    """
    progress = 10
    return {"status" : progress}
