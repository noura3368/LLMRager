import datetime, csv, sys
import os, requests
from .structured_output import generate_with_timing
import time, json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined

def info(message):
    """Print info message with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [INFO] {message}")


def get_available_templates(templates_dir, type):
    """Get list of available Jinja templates"""
    templates = None 
    print(templates_dir, "template dir!!!")
    try:
        templates_path = Path(templates_dir)
        if templates_path.exists():
            for file in templates_path.glob("*.jinja"):
                if type in file.name:
                    templates = file
            info(f"Found templates: {templates}")
        return templates
    except Exception as e:
        info(f"Error getting templates: {e}")
        return None 


def load_models_from_csv(csv_path):
    """Load model names from CSV file"""
    models = []
    csv_file = Path(csv_path)
    if csv_file.is_file():
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    model_name = row.get("Model Name", "").strip()
                    if model_name:
                        models.append(model_name)
            info(f"Loaded {len(models)} models from {csv_path}")
            return models
        except Exception as e:
            info(f"Error loading models from CSV: {e}")
            return []
    else: 
        info(f"CSV file not found at {csv_path}")
        return []

def render_template_and_generate(template_path, model, params, output_path, default_ollama_host, type, timeout=600):
    """Render template and generate structured response in-process"""
    # Build template environment
    print(template_path, "template path!!!")
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    
    jinja_template = env.get_template(template_path.name)
    
    # Render the template
    try:
        rendered_prompt = jinja_template.render(**params)
    except Exception as e:
        print(f"Error rendering template: {e}", file=sys.stderr)
        return False
    # Base prompt built purely from your Jinja template
    composed_prompt = rendered_prompt.strip()

    print("Generated prompt:")
    print(composed_prompt)
    print("\n" + "="*50 + "\n")

    try:
        # Generate structured response with timing
        structured_response, started_at, ended_at, elapsed_ms = generate_with_timing(
            model_name=model,
            prompt=composed_prompt,
            ollama_host=os.getenv("OLLAMA_BASE_URL", default_ollama_host),
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
        
        return response_json
        
    except Exception as e:
        info(f"Structured generation failed with error {e}, skipping output")
        print(f"❌ Error calling Ollama generate: {e}", file=sys.stderr)
        return False


def parse_results(response):
    """Parse the generated response and extract commands"""
    print(response, "parsing response")
    list_of_commands = []
    try:
        if isinstance(response, dict) and "response" in response:
            response_text = response["response"]
        elif isinstance(response, str):
            response_text = response
        else:
            info("Unexpected response format, expected dict with 'response' key or string")
            return []
        
        # Try parsing as JSON
        try:
            parsed = json.loads(response_text)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "command" in item:
                        list_of_commands.append(item["command"] )
            else:
                info("Parsed JSON is not a list, cannot extract commands")
            return list_of_commands
        except json.JSONDecodeError:
            info("Response is not valid JSON, cannot extract commands")
            return []
        
    except Exception as e:
        info(f"Error parsing results: {e}")
        return [] 

def main_func(extract_items, rag_output=None, number_of_commands=10, type="generate"):
    #config = load_config()
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
    MODELS = os.getenv("MODELS").split(',')
    PROMPTS = "llm_pipeline/prompts/original"
    #PROMPTS = os.getenv("PROMPTS")
    print("OLLAMA_BASE_URL", OLLAMA_BASE_URL)
    print("MODELS", MODELS)
    print("PROMPTS", PROMPTS)
    available_template = get_available_templates(PROMPTS, type)
    if not available_template:
        info(f"No templates found in {PROMPTS}. Exiting.")
        sys.exit(1)

    list_of_commands = [] # final list of commands from all the models 
   
    for model in MODELS:
        # Uses whatever value is set as env variable OLLAMA_BASE_URL, or defaulted config file value. 
        #resp = requests.post(f'{OLLAMA_BASE_URL}/api/pull', json={"name": model, "stream": False}, timeout=600)
        #resp.raise_for_status()
        info(f"Processing model: {model}")
        timestamp = str(int(time.time() * 1000000000))
        params = {
            "EXTRACTED_ITEMS": extract_items,
            "RAG_CONTEXT": rag_output,
            "NUMBER_OF_COMMANDS": number_of_commands
            
        }
                    
        # Run template and generate in-process
        output_path = Path(f"out/{model}_{timestamp}.json")
        success = render_template_and_generate(available_template, model, params, output_path, OLLAMA_BASE_URL, type)
        
        if not success:
            info(f"Model returned unstructured response, not included in output: {model}")
            continue
        else:
            parsed_results = parse_results(success)
            #print(f"Extracted commands from model {model}: {parsed_results}, total commands so far: {list_of_commands}")
            list_of_commands.extend(parsed_results)
    return list_of_commands
        
            
if __name__ == "__main__":
    try:
        info("Script starting with structured output")
        extract_items = []
        main_func(extract_items=extract_items)
    except KeyboardInterrupt:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Script failed with error: {e}")
        sys.exit(1)
