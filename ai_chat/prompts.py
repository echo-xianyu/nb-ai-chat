# prompts.py
# Build prompts to send to the AI

from typing import List, Dict, Optional, Any

# Import configuration
from .config import plugin_config
# Import database operations
from .data_source import get_impression
# Import utility functions
from .utils import get_current_formatted_time

# Message history is expected as List[Dict[str, Any]] from handlers.py
# Example dict structure (can be refined):
# {"user_id": "123", "sender": {"nickname": "Nick"}, "message": "Hello", "time": 1678886400}

async def build_prompt(message_history: List[Dict[str, Any]]) -> Optional[str]:
    """
    Build the main prompt to send to the AI based on message history, user impressions, and config.

    Args:
        message_history: List of recent message records (dictionaries).

    Returns:
        The constructed prompt string, or None if config is not loaded.
    """
    if not plugin_config:
        print("AI Chat Plugin: Error - Configuration not loaded, cannot build prompt.")
        return None

    user_content_parts = []
    # Extract unique user IDs from the history list of dictionaries
    involved_users = set(record.get("user_id", "unknown") for record in message_history if record.get("user_id"))

    # Get impressions for involved users
    user_impressions: Dict[str, Optional[str]] = {}
    for user_id in involved_users:
        try:
            impression = await get_impression(user_id)
            user_impressions[user_id] = impression if impression else "" # Use empty string for None
        except Exception as e:
            print(f"AI Chat Plugin: Error getting impression for user {user_id}: {e}")
            user_impressions[user_id] = "" # Default to empty on error

    # Format user messages and impressions according to the specified format:
    # {"QQ1":[ImpressionA]} MessageText1 {"QQ2":[ImpressionB]} MessageText2 ...
    for record in message_history:
        user_id = record.get("user_id")
        message_text = record.get("message")

        if not user_id or message_text is None: # Skip records without user_id or message
            continue

        impression_str = user_impressions.get(user_id, "") # Get impression, default to empty string

        # Escape potential special characters in impression_str if needed (e.g., quotes within JSON-like string)
        # Basic escaping for double quotes inside the impression string:
        impression_str_escaped = impression_str.replace('"', '\\"')

        # Format: {"QQ":[Impression]} Message
        # Ensure the impression string is properly quoted within the JSON-like structure
        user_content_parts.append(f'{{"{user_id}":["{impression_str_escaped}"]}} {message_text}')

    # Join the parts with a space as specified
    user_content = " ".join(user_content_parts)

    # Get current formatted time
    try:
        current_time_str = get_current_formatted_time()
    except Exception as e:
        print(f"AI Chat Plugin: Error getting formatted time: {e}")
        current_time_str = "Unknown" # Fallback time

    # Assemble the final prompt using the exact specified format
    # Ensure newline characters are correctly placed
    final_prompt = f"<system:{plugin_config.system_prompt}>\n<user:{user_content}>\ncurrent time: {current_time_str}"

    return final_prompt


async def build_impression_prompt(user_id: str, user_messages: List[str]) -> Optional[str]:
    """
    Build the prompt used to generate a user's impression.

    Args:
        user_id: The target user's QQ ID.
        user_messages: List of the user's messages within the context.

    Returns:
        The constructed impression generation prompt string, or None if config is not loaded or template fails.
    """
    if not plugin_config:
        print("AI Chat Plugin: Error - Configuration not loaded, cannot build impression prompt.")
        return None

    # Get the previous impression
    try:
        previous_impression = await get_impression(user_id)
        if not previous_impression:
            previous_impression = "无" # Explicitly state "None" if no previous impression
    except Exception as e:
        print(f"AI Chat Plugin: Error getting previous impression for user {user_id}: {e}")
        previous_impression = "获取失败" # Indicate failure

    # Format the user message list
    # Ensure messages don't break the formatting, e.g., by removing newlines within a single message
    messages_str = "\n".join(f"- {msg.replace(chr(10), ' ').replace(chr(13), '')}" for msg in user_messages)

    # Fill the template from the configuration
    try:
        impression_prompt_filled = plugin_config.impression_prompt.format(
            previous_impression=previous_impression,
            user_messages=messages_str
        )
        return impression_prompt_filled
    except KeyError as e:
        print(f"AI Chat Plugin: Error - Missing variable in impression_prompt template: {e}. Check config.yaml.")
        return None
    except Exception as e:
        print(f"AI Chat Plugin: Error building impression prompt: {e}")
        return None

# --- Example Usage (for testing, keep commented out) ---
# async def main():
#     # ... (example code remains commented) ...
#     pass

# if __name__ == "__main__":
#     # ... (example code remains commented) ...
#     pass