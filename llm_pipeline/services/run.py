import datetime, csv, sys
from collections import defaultdict
import os, requests
from pathlib import Path
from services.prompt_builder import build_final_prompt
import time, json
from services.structured_output import generate_with_timing
DEFAULT_MODEL = "devstral:24b"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


def info(message):
    """Print info message with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [INFO] {message}")


def load_config(config_file="./config.txt"):
    config = defaultdict()
    print(os.path.exists(config_file))
    try:
        if not os.path.exists(config_file):
            info(f"Config file {config_file} not found, using defaults")
            return False
            
        with open(config_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
            
                    config[key] = value
                else:
                    info(f"Warning: Invalid config line {line_num}: {line}")
        
        info(f"Loaded configuration from {config_file}")
        return config
        
    except Exception as e:
        info(f"Error loading config file {config_file}: {e}")
        info("Using default configuration")
        return False


def load_models_from_csv(csv_path, model_start):
    """Load model names from CSV file"""
    models = []
    index = 0
    csv_file = Path(csv_path)
    if csv_file.is_file():
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    model_name = row['Model Name'].strip()
                    index += 1
                    if model_name and index >= model_start:  # Skip empty rows
                        models.append(model_name)
            info(f"Loaded {len(models)} models from {csv_path}")
            return models
        except Exception as e:
            info(f"Error loading models from CSV: {e}")
            return []
    else: 
        info(f"CSV file not found at {csv_path}")
        return False

def render_template_and_generate(model, params, output_path,prompt, timeout=600, rag_context=""):
    """Render template and generate structured response in-process"""

    # Base prompt built purely from your Jinja template
    base_prompt = prompt.strip()

    if rag_context:
        # Manual-aware final prompt
        
        composed_prompt = (
            f"{base_prompt}\n\n"
            "You can use the information in the device manual context below and the instructions.\n"
            f"DEVICE MANUAL CONTEXT:\n{rag_context}\n"
        )
    else:
        # Fallback: no RAG, just the original prompt
        composed_prompt = base_prompt
    
    print("Generated prompt:")
    print(composed_prompt)
    print("\n" + "="*50 + "\n")

    try:
        # Generate structured response with timing
        structured_response, started_at, ended_at, elapsed_ms = generate_with_timing(
            model_name=model,
            prompt=composed_prompt,
            ollama_host=OLLAMA_URL,
            timeout=timeout
        )
        # Convert to the format expected by the original system
        output_text = json.dumps([cmd.model_dump() for cmd in structured_response.commands], indent=2)
        
        # Create response JSON
        response_json = {
            "model": model,
            "params": params,
            "prompt": composed_prompt,
            "time": elapsed_ms,
            "response": output_text,
            "structured": True,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat()
        }
        
        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(response_json, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Output written to: {output_path}")
        print("✅ Used structured output with outlines")
        
        return True
        
    except Exception as e:
        info(f"Structured generation failed with error {e}, skipping output")
        print(f"❌ Error calling Ollama generate: {e}", file=sys.stderr)


def main(extract_items, rag_output=None):
        prompt = build_final_prompt(extracted_items=extract_items, rag_context=rag_output)
        config = load_config()
        models = []
        if config and "models_csv" in config:
            models = load_models_from_csv(config["models_csv"])
        print(f"Inputted models {models}")
        if not models:
            info("No models loaded from CSV file. Using default model " + DEFAULT_MODEL)
            models = models.append(DEFAULT_MODEL)
        print(f"Models to process: {models}")
        for model in models:
             resp = requests.post(f"{OLLAMA_URL}/api/pull", json={"model": model, "stream": False}, timeout=600)
             resp.raise_for_status()
             info(f"Processing model: {model}")
             timestamp = str(int(time.time() * 1000000000))
             params = {
                    #"ITERATION": i
                }
                    
             # Run template and generate in-process
             output_path = Path(f"out/{model}_{timestamp}.json")
             success = render_template_and_generate(model, params, output_path, prompt, rag_output)
                    
             if not success:
                info(f"Model returned unstructured response, not included in output: {model}")
                continue


if __name__ == "__main__":
    try:
        info("Script starting with structured output")
        extract_items = []
        main(extract_items=extract_items)
    except KeyboardInterrupt:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Script failed with error: {e}")
        sys.exit(1)

