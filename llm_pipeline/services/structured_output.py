#!/usr/bin/env python3
"""
Structured output classes for LLM responses using Ollama's native structured output.
"""

from typing import List, Dict, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from time import perf_counter
import json
import ollama


class SecurityTestCommand(BaseModel):
    """
    A single security test command with parameters.
    """
    command: str = Field(
        description="The command and parameters string to be sent to the target device"
    )


class SecurityTestResponse(BaseModel):
    """
    A list of security test commands for testing a target device.
    """
    commands: List[SecurityTestCommand] = Field(
        description="List of security test commands to execute against the target"
    )


# Module-level cache for Ollama clients
_client_cache: Dict[str, ollama.Client] = {}


def get_client_cached(ollama_host: str = None, timeout: float = 500) -> ollama.Client:
    cache_key = ollama_host or "default"
    if cache_key not in _client_cache:
        _client_cache[cache_key] = ollama.Client(host=ollama_host, timeout=timeout)
    return _client_cache[cache_key]


def generate_with_timing(model_name: str, prompt: str, ollama_host: str = None, timeout: float = 500):
    """
    Generate structured response with timing information using Ollama's native structured output.

    Args:
        model_name: The name of the Ollama model to use
        prompt: The prompt to send to the model
        ollama_host: Ollama host URL (e.g., http://localhost:11434)
        timeout: Request timeout in seconds

    Returns:
        Tuple of (SecurityTestResponse, started_at, ended_at, elapsed_ms)
        where started_at and ended_at are datetime objects in UTC
    """
    client = get_client_cached(ollama_host, timeout)

    started_at = datetime.now(timezone.utc)

    response = client.generate(
        model=model_name,
        prompt=prompt,
        format=SecurityTestResponse.model_json_schema(),
    )

    ended_at = datetime.now(timezone.utc)
    elapsed_ms = int((ended_at - started_at).total_seconds() * 1000)

    structured_response = SecurityTestResponse.model_validate_json(response.response)

    return structured_response, started_at, ended_at, elapsed_ms
