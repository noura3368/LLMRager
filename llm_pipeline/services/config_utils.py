import datetime, os

def info(message):
    """Print info message with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [INFO] {message}")

def load_config(config_file="./config.txt"):
    config = {}
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
                    continue
        
        info(f"Loaded configuration from {config_file}")
        return config
        
    except Exception as e:
        info(f"Error loading config file {config_file}: {e}")
        info("Using default configuration")
        return False