import datetime, csv, sys
import os, requests
from services.structured_output import generate_with_timing
import time, json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from services.config_utils import load_config
# default model if no CSV provided in config.txt or CSV loading fails
DEFAULT_MODEL = "devstral:24b"

def info(message):
    """Print info message with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [INFO] {message}")


def get_available_templates(templates_dir, type):
    """Get list of available Jinja templates"""
    templates = None 
    try:
        templates_path = Path(templates_dir)
        if templates_path.exists():
            for file in templates_path.glob("*.jinja") and type in file.name:
                templates = file.name 
        info(f"Found {len(templates)} templates: {templates}")
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

def render_template_and_generate(template_path, model, params, output_path, prompt, default_ollama_host, type, timeout=600):
    """Render template and generate structured response in-process"""
    # Build template environment
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
            ollama_host=os.getenv("OLLAMA_URL", default_ollama_host),
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
                        list_of_commands.append(item["command"])
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
    config = load_config()
    # maybe empty strings below 
    default_ollama_url = "http://localhost:11434"
    default_prompts = "/app/prompts/original"
    models_csv = None 
    if config: # if config file exists and we want to use it 
        if config.get("USE_DOCKER_ENV_FILE") and config.get("USE_DOCKER_ENV_FILE").lower() == "true":
            if config.get("OLLAMA_URL"): # save all the values as environment varibles
                os.environ["OLLAMA_URL"] = config["OLLAMA_URL"]
            if config.get("PROMPTS"):
                os.environ["PROMPTS"] = config["PROMPTS"]
            if config.get("MODELS_CSV"): # no system environment variable for MODELS_CSV. use default value if models_csv is not set or file does not exist.
                models_csv = config["MODELS_CSV"]
        else: # if we are supposed to use system environment variables instead, save the values in config file as backup instead 
            # set the defaults values from config in case system environment variables are not set. 
            if config.get("OLLAMA_URL"):
                default_ollama_url = config["OLLAMA_URL"]
            # so if no prompts are inputted from system var or config, it will default to the original prompt in the prompts folder
            if config.get("PROMPTS"):
                default_prompts = config["PROMPTS"]
            

    # Get available template, either modify or generate type. If no template found, exit the program.
    # original template exists in prompts/original 
    # user can introduce new templates by adding them to the prompts folder and specifying the type in the template name (e.g., modify or generate) and the folder path in config.txt. 
    available_template = get_available_templates(os.getenv("PROMPTS", default_prompts))
    if not available_template:
        info(f"No templates found in {os.getenv("PROMPTS", default_prompts)}. Exiting.")
        sys.exit(1)
    
    models = [DEFAULT_MODEL]

    if models_csv: 
        list_of_models = load_models_from_csv(models_csv)
        if len(list_of_models) > 0:
            models = list_of_models
        print(f"Models to process {models}")
    list_of_commands = [] # final list of commands from all the models 
   
    for model in models:
        # Uses whatever value is set as env variable OLLAMA_URL, or defaulted config file value. 
        resp = requests.post(f'{os.getenv("OLLAMA_URL", default_ollama_url)}/api/pull', json={"name": model, "stream": False}, timeout=400)
        resp.raise_for_status()
        info(f"Processing model: {model}")
        timestamp = str(int(time.time() * 1000000000))
        params = {
            "EXTRACTED_ITEMS": extract_items,
            "RAG_CONTEXT": rag_output,
            "NUMBER_OF_COMMANDS": number_of_commands
            
        }
                    
        # Run template and generate in-process
        output_path = Path(f"out/{model}_{timestamp}.json")
        success = render_template_and_generate(available_template, model, params, output_path, prompt, os.getenv("OLLAMA_URL", default_ollama_url), type)
        
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
