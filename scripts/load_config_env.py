#!/usr/bin/env python3
import os
import sys
from pathlib import Path


def get_config_value(key: str, config_file: Path) -> str | None:
    if not config_file.is_file():
        return None
    
    last_value = None
    with config_file.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            left, right = line.split("=", 1)
            if left.strip() == key:
                last_value = right.strip()
    print(last_value, f"config value for {key} from {config_file}")
    return last_value


def resolve_value(
    key: str,
    default: str,
    config_file: Path,
    use_docker_env_file_resolved: str,
) -> str:
    print(config_file, "config file!!!")
    cfg = get_config_value(key, config_file)
    env_val = os.environ.get(key)
    print(f"Resolving {key}: cfg='{cfg}', env='{env_val}', default='{default}' with USE_DOCKER_ENV_FILE_RESOLVED='{use_docker_env_file_resolved}'")
    print(use_docker_env_file_resolved, type(use_docker_env_file_resolved))
    if use_docker_env_file_resolved == "true":
        if cfg:
            print("usig config value", cfg)
            return cfg
        if env_val:
            return env_val
        return default
    else:
        if env_val:
            return env_val
        if cfg:
            return cfg
        return default


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    config_file = Path(
        os.environ.get(
            "CONFIG_FILE",
            str(script_dir.parent / "llm_pipeline" / "services" / "config.txt"),
        )
    )

    use_docker_env_file_resolved = (
        (get_config_value("USE_DOCKER_ENV_FILE", config_file) or "false")
        .strip()
        .lower()
    )

    ollama_url = resolve_value(
        "OLLAMA_URL",
        "http://localhost:11434",
        config_file,
        use_docker_env_file_resolved,
    )
    print(ollama_url, "ollama_url")
    models_csv = resolve_value(
        "MODELS_CSV",
        "",
        config_file,
        use_docker_env_file_resolved,
    )
    prompts = resolve_value(
        "PROMPTS",
        "/app/llm_pipeline/prompts/original",
        config_file,
        use_docker_env_file_resolved,
    )
    pre_processing_model = resolve_value(
        "PRE_PROCESSING_MODEL",
        "qwen2.5:7b",
        config_file,
        use_docker_env_file_resolved,
    )

    os.environ["OLLAMA_URL"] = ollama_url
    os.environ["MODELS_CSV"] = models_csv
    os.environ["PROMPTS"] = prompts
    os.environ["PRE_PROCESSING_MODEL"] = pre_processing_model
    os.environ["OLLAMA_BASE_URL"] = ollama_url

    print(f"CONFIG_FILE={config_file}")
    print(f"USE_DOCKER_ENV_FILE_RESOLVED={use_docker_env_file_resolved}")
    print(f"OLLAMA_URL={ollama_url}")
    print(f"MODELS_CSV={models_csv}")
    print(f"PROMPTS={prompts}")
    print(f"PRE_PROCESSING_MODEL={pre_processing_model}")

    if len(sys.argv) < 2:
        print("No command provided", file=sys.stderr)
        return 1

    os.execvpe(sys.argv[1], sys.argv[1:], os.environ)


if __name__ == "__main__":
    raise SystemExit(main())