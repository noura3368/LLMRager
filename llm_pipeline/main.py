from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from llm_pipeline.services.rag_service import retrieve_context
from llm_pipeline.services.run import main_func
from llm_pipeline.utils.communication_utils import get_async, post_async, delete_async
from llm_pipeline.utils.ollama_utils import parse_models, pull_model_streamer

import os

app = FastAPI()

#OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

class GenerateRequest(BaseModel):
    items: list[str] = Field(..., min_length=1)
    number_of_commands: int = Field(..., ge=1)

class ModelRequest(BaseModel):
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
    
    curr_model_url = f"{OLLAMA_BASE_URL}/api/ps"
    list_models_url = f"{OLLAMA_BASE_URL}/api/tags"
    
    # curr_resp = await get_async(curr_model_url, 140)
    all_resp = await get_async(list_models_url, 140)
    
    all_models = parse_models(all_resp)
    # curr_model = parse_models(curr_resp)
    
    return {
        "active_model": os.environ["MODELS"],
        "all_models": all_models
    }


@app.post("/pull_model")
async def list_models(payload: ModelRequest):
    """ 
        Pull the model with streaming response for progress
    """

    url = f"{OLLAMA_BASE_URL}/api/pull"
    
    return StreamingResponse(
        pull_model_streamer(payload.model, url), 
        media_type="application/x-ndjson"
    )


@app.post("/set_model")
async def list_models(payload: ModelRequest):
    """ 
        Set a new model to be used by ollama
    """
    os.environ["MODELS"] = payload.model
    return {"model": os.environ["MODELS"]}


@app.delete("/delete_model")
async def delete_model(payload: ModelRequest):
    url = f"{OLLAMA_BASE_URL}/api/delete"

    result = await delete_async(url, {"name": payload.model})

    if isinstance(result, dict) and "error" in result:
        # raise HTTPException(
        #     status_code=400,
        #     detail=result["error"]
        # )
        return {
        "status": "error",
        "message": result['error']
    }

    return {
        "status": "ok",
        "message": f"deleted {payload.model}"
    }