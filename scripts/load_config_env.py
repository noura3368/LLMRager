import os
import sys
from pathlib import Path
from dotenv import dotenv_values
import shlex
import logging 
DEFAULT_MODEL = "qwen2.5:32b"
DEFAULT_PREPROCESSING_MODEL = "qwen2.5:7b"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def main():
    
    env_file = dotenv_values(".env") # Load .env file if it exists
    use_env_file = env_file.get("USE_ENV_FILE", "false").lower() == "true"

    logging.info(f"Use env file? = {use_env_file}")

    def get_config(name: str, default: str | None = None) -> str | None:
        if use_env_file:
            return env_file.get(name, os.environ.get(name, default))
        return os.environ.get(name, env_file.get(name, default))

    
    OLLAMA_BASE_URL = get_config("OLLAMA_BASE_URL", None)
    PRE_PROCESSING_MODEL = get_config("PRE_PROCESSING_MODEL", DEFAULT_PREPROCESSING_MODEL)
    MODELS = get_config("MODELS", DEFAULT_MODEL)
    DOCLING_SERVE_URL = get_config("DOCLING_SERVE_URL", None)

    if OLLAMA_BASE_URL is None:
        logging.info("Error: OLLAMA_BASE_URL is not set in environment variables or .env file.")
        return 1
    if get_config("PRE_PROCESSING_MODEL") is None:
        logging.info(f"Warning: PRE_PROCESSING_MODEL is not set in environment variables or .env file. Setting preprocessing model to default {DEFAULT_PREPROCESSING_MODEL}.")
    if get_config("MODELS") is None:
        logging.info(f"Warning: MODELS is not set in environment variables or .env file. Setting MODELS to default {DEFAULT_MODEL}.")
        return 1 
    if DOCLING_SERVE_URL is None:
        logging.info("Error: DOCLING_SERVE_URL is not set in environment variables or .env file.")
        return 1
    
    exports = {
        "OLLAMA_BASE_URL": OLLAMA_BASE_URL,
        "PRE_PROCESSING_MODEL": PRE_PROCESSING_MODEL,
        "MODELS": MODELS,
        "DOCLING_SERVE_URL": DOCLING_SERVE_URL,
    }

    for key, value in exports.items():
        logging.info(f"export {key}={shlex.quote(value)}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())