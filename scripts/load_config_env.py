import os
import sys
from pathlib import Path
from dotenv import dotenv_values
import shlex

DEFAULT_MODEL = "qwen2.5:32b"
DEFAULT_PREPROCESSING_MODEL = "qwen2.5:7b"
def main():
    env_file = dotenv_values(".env") # Load .env file if it exists
    use_env_file = env_file.get("USE_ENV_FILE", "true").lower() == "true"

    print(use_env_file, 'use env', file=sys.stderr)
    def get_config(name: str, default: str | None = None) -> str | None:
        if use_env_file:
            print(name, os.environ.get(name), env_file.get(name), 'config value', file=sys.stderr)
            return env_file.get(name, os.environ.get(name, default))
        return os.environ.get(name, env_file.get(name, default))

    print(os.environ.get("MODELS_CSV"), 'model env', file=sys.stderr)
    OLLAMA_URL = get_config("OLLAMA_URL", None)
    PRE_PROCESSING_MODEL = get_config("PRE_PROCESSING_MODEL", DEFAULT_PREPROCESSING_MODEL)
    PROMPTS = get_config("PROMPTS", None)
    MODELS_CSV = get_config("MODELS_CSV", DEFAULT_MODEL)
    DOCLING_SERVE_URL = get_config("DOCLING_SERVE_URL", None)

    if OLLAMA_URL is None:
        print("Error: OLLAMA_URL is not set in environment variables or .env file.", file=sys.stderr)
        return 1
    if get_config("PRE_PROCESSING_MODEL") is None:
        print(f"Warning: PRE_PROCESSING_MODEL is not set in environment variables or .env file. Setting preprocessing model to default {DEFAULT_PREPROCESSING_MODEL}.", file=sys.stderr)
    if get_config("MODELS_CSV") is None:
        print(f"Warning: MODELS_CSV is not set in environment variables or .env file. Setting MODELS_CSV to default {DEFAULT_MODEL}.", file=sys.stderr)
    if PROMPTS is None:
        print("Error: PROMPTS is not set in environment variables or .env file.", file=sys.stderr)
        return 1 
    if DOCLING_SERVE_URL is None:
        print("Error: DOCLING_SERVE_URL is not set in environment variables or .env file.", file=sys.stderr)
        return 1
    
    exports = {
        "OLLAMA_URL": OLLAMA_URL,
        "PRE_PROCESSING_MODEL": PRE_PROCESSING_MODEL,
        "PROMPTS": PROMPTS,
        "MODELS_CSV": MODELS_CSV,
        "DOCLING_SERVE_URL": DOCLING_SERVE_URL,
    }

    for key, value in exports.items():
        print(f"export {key}={shlex.quote(value)}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())