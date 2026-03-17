from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from .services.rag_service import retrieve_context
from .services.run import main_func

app = FastAPI()


class GenerateRequest(BaseModel):
    items: list[str] = Field(..., min_length=1)
    number_of_commands: int = Field(..., ge=1)


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
    