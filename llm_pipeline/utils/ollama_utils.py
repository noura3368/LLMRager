import httpx

def parse_models(request):
    return [
        {
            "name": x.get("name", "NA"),
            "parameter_size": x.get("details", {}).get("parameter_size", "NA"),
            "quantization_level": x.get("details", {}).get("quantization_level", "NA"),
            "size": x.get("size", "NA"),
        }
        for x in request["models"]
    ]    

async def pull_model_streamer(model_name, url):
    """
        Stream back model download progress to user
    """
    payload = {"model": model_name, "stream": True}
    
    async with httpx.AsyncClient(timeout=None) as client:
        # Request a streaming response from Ollama
        async with client.stream("POST", url, json=payload) as response:
            async for chunk in response.aiter_text():
                if chunk:
                    # Forward the chunk exactly as it comes (JSON)
                    yield chunk