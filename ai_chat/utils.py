# utils.py
# 辅助函数

import time
from typing import List, Optional, Dict, Any
from nonebot.adapters.onebot.v11 import Bot # Import Bot for API calls

# --- 时间相关 ---
def get_current_formatted_time() -> str:
    """
    获取当前时间，格式为 YY/MM/DD/HH:MM。
    """
    return time.strftime("%y/%m/%d/%H:%M", time.localtime())

# --- Message History ---
async def get_message_history(bot: Bot, group_id: str, count: int = 30) -> List[Dict[str, Any]]:
    """
    Fetches recent group message history using the get_group_msg_history API.

    Args:
        bot: The Bot instance.
        group_id: The target group ID.
        count: The maximum number of messages to retrieve.

    Returns:
        A list of message dictionaries, ordered chronologically (oldest first, if possible).
        Returns an empty list if fetching fails or no history is available.
        Each dictionary aims to contain: 'user_id', 'sender':{'nickname', 'user_id'}, 'message', 'time'.
    """
    if not group_id:
        print("AI Chat Plugin: Error - group_id is required for get_message_history.")
        return []

    processed_history = []
    try:
        # Note: The standard get_group_msg_history might not support a 'count' parameter directly.
        # It often returns a batch starting from a sequence number. We fetch a batch and then slice.
        # Some implementations might return messages in reverse chronological order.
        print(f"AI Chat Plugin: Attempting to fetch message history for group {group_id} via API...")
        raw_history = await bot.call_api("get_group_msg_history", group_id=int(group_id)) # Assuming group_id needs to be int

        if not raw_history or not isinstance(raw_history.get("messages"), list):
            print(f"AI Chat Plugin: No valid message history returned for group {group_id}.")
            return []

        # Process the raw history (list of message objects from OneBot spec)
        # The exact structure of each message object can vary slightly by implementation
        # We need 'user_id', 'message', 'time', 'sender' (with 'nickname')
        raw_messages = raw_history["messages"]
        print(f"AI Chat Plugin: Received {len(raw_messages)} raw messages for group {group_id}.")

        for msg in raw_messages:
            if not isinstance(msg, dict): continue # Skip invalid entries

            sender = msg.get("sender", {})
            user_id = str(sender.get("user_id", "unknown"))
            nickname = sender.get("nickname", user_id) # Fallback nickname to user_id
            message_content = msg.get("message", "") # Handle potential missing message content
            timestamp = msg.get("time", 0) # Get timestamp

            # Convert message segments if necessary (e.g., extract text from complex messages)
            # For simplicity, we'll assume 'message' is mostly text or handle basic cases.
            # A more robust solution would parse the message segments array if 'message' is a list.
            if isinstance(message_content, list):
                 # Attempt to extract text from message segments
                 text_parts = [seg.get("data", {}).get("text", "") for seg in message_content if seg.get("type") == "text"]
                 message_text = "".join(text_parts).strip()
            elif isinstance(message_content, str):
                 message_text = message_content.strip()
            else:
                 message_text = "" # Skip if message format is unexpected

            if user_id != "unknown" and message_text: # Only include messages with known sender and content
                processed_history.append({
                    "user_id": user_id,
                    "sender": {"nickname": nickname, "user_id": user_id},
                    "message": message_text,
                    "time": timestamp
                })

        # Sort by time just in case the API doesn't guarantee order (oldest first)
        processed_history.sort(key=lambda x: x.get("time", 0))

        # Return the last 'count' messages
        final_history = processed_history[-count:]
        print(f"AI Chat Plugin: Processed {len(final_history)} messages for history.")
        return final_history

    except Exception as e:
        # Catch potential API errors (like ActionFailed) or processing errors
        print(f"AI Chat Plugin: Error fetching or processing message history for group {group_id}: {e}")
        return [] # Return empty list on failure

# --- 其他辅助函数 (如果需要) ---