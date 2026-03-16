#!/usr/bin/env python3
"""
Structured output classes for LLM responses using outlines package.
"""

from typing import List, Optional, Dict, Tuple, Any
from pydantic import BaseModel, Field
import outlines
from outlines import models
from outlines.generator import Generator
from datetime import datetime, timezone
from time import perf_counter
import requests
import json
import csv
from pathlib import Path
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


# Module-level cache for generators to avoid re-initialization
_generator_cache: Dict[Tuple[str, str], Generator] = {}


def get_structured_generator_cached(model_name: str, ollama_host: str = None, timeout=500):
    """
    Get a cached structured generator for the given model and host.
    Creates and caches the generator if it doesn't exist.
    
    Args:
        model_name: The name of the Ollama model to use
        ollama_host: Optional Ollama host URL (e.g., http://localhost:11434)
        
    Returns:
        A cached generator that enforces the SecurityTestResponse schema
    """
    # Use "default" as key when ollama_host is None
    cache_key = (model_name, ollama_host or "default")
    
    if cache_key not in _generator_cache:
        
        client = ollama.Client(host=ollama_host, timeout=timeout)
        
        # Create the model using the correct API
        model = models.ollama.from_ollama(client, model_name)
        
        # Create a structured generator using the correct API
        gen = Generator(model, SecurityTestResponse)
        
        # Cache the generator
        _generator_cache[cache_key] = gen
    
    return _generator_cache[cache_key]


def generate_with_timing(model_name: str, prompt: str, ollama_host: str = None, timeout:float=500):
    """
    Generate structured response with timing information.
    
    Args:
        model_name: The name of the Ollama model to use
        prompt: The prompt to send to the model
        ollama_host: Ollama host URL (e.g., http://localhost:11434)
        
    Returns:
        Tuple of (SecurityTestResponse, started_at, ended_at, elapsed_ms)
        where started_at and ended_at are datetime objects in UTC
    """

    # Get cached generator
    print("in structured output, getting generator")
    gen = get_structured_generator_cached(model_name, ollama_host, timeout)
    started_at = datetime.now(timezone.utc)
    # Generate structured response
    response = gen(prompt)
    
    ended_at = datetime.now(timezone.utc)
    elapsed_ms = int((ended_at - started_at).total_seconds() * 1000)
    
    # Convert to the expected format
    if hasattr(response, 'commands'):
        # Response is already a SecurityTestResponse object
        structured_response = response
    elif isinstance(response, str):
        try:
            parsed_response = json.loads(response)
            structured_response = SecurityTestResponse(**parsed_response)
        except Exception:
            print("Incorrect model format...")
            structured_response = response
    elif isinstance(response, dict):
        # Response might be a dict, convert it
        structured_response = SecurityTestResponse(**response)
    return structured_response, started_at, ended_at, elapsed_ms
