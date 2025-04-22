import yaml
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import Optional

# --- Default Configuration Content ---
DEFAULT_CONFIG_YAML = """\
# OpenAI compatible API endpoint address
api_url: "https://api.openai.com/v1/chat/completions"

# API Key (Please replace with your valid key)
api_key: "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Default System Prompt
system_prompt: "You are a friendly and helpful AI assistant."

# Prompt template for generating user impressions
# Available variables: {user_messages} (list of recent user messages), {previous_impression} (user's previous impression)
impression_prompt: |
  Please generate a concise impression description (max 100 characters) for the user based on their recent messages and previous impression (if any).
  Previous impression: {previous_impression}
  Recent messages:
  {user_messages}
  Generated impression:

# Base probability for random replies (float between 0.0 and 1.0)
# Plugin attempts a random reply with this probability upon receiving a group message (subject to min interval)
base_reply_probability: 0.05

# Minimum reply interval per group chat (in seconds)
# Prevents overly frequent random replies
min_reply_interval: 300

# Maximum token count for a single AI reply
max_tokens: 1000

# Model name to use for chat completions (e.g., gpt-3.5-turbo, gpt-4)
chat_model: "gpt-3.5-turbo"

# Model name to use for impression generation (can be same as chat_model or a different one)
impression_model: "gpt-3.5-turbo"
"""

# --- Configuration Model ---
class Config(BaseModel):
    api_url: str = "https://api.openai.com/v1/chat/completions"
    api_key: str = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    system_prompt: str = "You are a friendly and helpful AI assistant."
    impression_prompt: str = Field(
        default=(
            "Please generate a concise impression description (max 100 characters) for the user based on their recent messages and previous impression (if any).\n"
            "Previous impression: {previous_impression}\n"
            "Recent messages:\n"
            "{user_messages}\n"
            "Generated impression:"
        )
    )
    base_reply_probability: float = Field(default=0.05, ge=0.0, le=1.0)
    min_reply_interval: int = Field(default=300, gt=0)
    max_tokens: int = Field(default=1000, gt=0)
    chat_model: str = "gpt-3.5-turbo"
    impression_model: str = "gpt-3.5-turbo" # Add the impression_model field
    context_length: int = Field(default=30, gt=0, le=100) # Fixed at 30, but configurable for future adjustments
    impression_min_messages: int = Field(default=5, gt=0) # Fixed at 5, but configurable

    @validator('api_key')
    def check_api_key(cls, v):
        if v == "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" or not v:
            raise ValueError("Please configure a valid api_key in config.yaml")
        return v

# --- Configuration File Path ---
CONFIG_DIR = Path("data/AI_chat")
CONFIG_PATH = CONFIG_DIR / "config.yaml"

# --- Load Configuration ---
def load_config() -> Config:
    """Load plugin configuration.

    Creates a default configuration file if it does not exist.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_PATH.is_file():
        print(f"Configuration file not found at {CONFIG_PATH}, creating default config...")
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(DEFAULT_CONFIG_YAML)
            print(f"Default configuration file created at {CONFIG_PATH}. Please edit api_key and other settings.")
            # Raise an error on first creation to prompt user modification, avoiding running with default invalid key
            raise ValueError(f"Please modify the api_key in the default configuration file {CONFIG_PATH} before starting.")
        except IOError as e:
            print(f"Failed to create default configuration file: {e}")
            raise

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
            if not isinstance(config_data, dict):
                 raise TypeError("Configuration file format error, expected a YAML dictionary.")
            # Add fixed values even if not explicitly in the config file
            config_data['context_length'] = 30
            config_data['impression_min_messages'] = 5
            return Config.parse_obj(config_data)
    except FileNotFoundError:
        # Should not happen due to the check above, but handle defensively
        print(f"Error: Configuration file {CONFIG_PATH} not found.")
        raise
    except yaml.YAMLError as e:
        print(f"Failed to parse configuration file {CONFIG_PATH}: {e}")
        raise
    except Exception as e: # Handle Pydantic validation errors etc.
        print(f"Error loading or validating configuration {CONFIG_PATH}: {e}")
        raise

# Attempt to load config when the module is imported
plugin_config: Optional[Config] = None # Define with type hint
try:
    plugin_config = load_config()
except Exception as e:
    # If loading fails (e.g., first creation prompting user edit), set to None
    print(f"Critical error during configuration initialization: {e}")
    plugin_config = None
    # print("Configuration loading failed, the plugin might not work correctly. Please check the config file or error messages.") # Keep original commented-out print