import os
import json
from typing import Dict, Any

# Default configuration values
DEFAULT_CONFIG = {
    "LOG_LEVEL": "INFO",
    "DEFAULT_SCAN_DIRECTORY": ".",
    "RETRY_TRIES": 3,
    "RETRY_DELAY": 1.0,
    "RETRY_BACKOFF": 2.0,
    "MARKDOWN_READ_RETRY_TRIES": 3,
    "MARKDOWN_READ_RETRY_DELAY": 0.1
}


def load_config() -> Dict[str, Any]:
    """
    Loads configuration values from config.json (if it exists) and environment variables.
    Values from environment variables override values from config.json.
    Missing values fall back to DEFAULT_CONFIG.
    """
    config = DEFAULT_CONFIG.copy()

    # Load from config.json if it exists
    config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            # We print since logging might not be configured yet
            print(f"Warning: Failed to load config.json: {e}")

    # Override with environment variables
    # Only try to cast to int/float for numeric types
    for key, default_value in DEFAULT_CONFIG.items():
        if key in os.environ:
            env_val = os.environ[key]
            if isinstance(default_value, int):
                try:
                    config[key] = int(env_val)
                except ValueError:
                    print(f"Warning: Invalid integer for {key} in environment variable.")
            elif isinstance(default_value, float):
                try:
                    config[key] = float(env_val)
                except ValueError:
                    print(f"Warning: Invalid float for {key} in environment variable.")
            else:
                config[key] = env_val

    return config


# Global configuration instance
APP_CONFIG = load_config()
