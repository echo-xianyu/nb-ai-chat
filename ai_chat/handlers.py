# handlers.py
# Message handling and event response logic

from nonebot import on_message, on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
import random
import time
import httpx # Import httpx for API calls later
from typing import List, Dict, Any # For type hinting

# Import configuration
from .config import plugin_config
# Import database operations
from .data_source import (
    is_blacklisted,
    get_group_setting,
    update_group_last_reply_time,
    add_to_blacklist,
    remove_from_blacklist,
    update_group_enabled,
    get_impression,
    update_impression,
)
# Import Prompt building functions
from .prompts import build_prompt, build_impression_prompt
# Import utility functions
from .utils import get_current_formatted_time, get_message_history # get_message_history is a placeholder

# --- Constants (will be read from config later) ---
CONTEXT_LENGTH = 30
IMPRESSION_MIN_MESSAGES = 5

# --- Group Message Handling ---
group_message_handler = on_message(priority=50, block=False) # block=False allows other plugins

@group_message_handler.handle()
async def handle_group_message(bot: Bot, event: GroupMessageEvent, matcher: Matcher):
    """Handles incoming group messages, checks permissions, and triggers AI response."""
    if not plugin_config: # Check if config loaded successfully
        return

    user_id = str(event.user_id)
    group_id = str(event.group_id)
    message_text = event.get_plaintext().strip()
    is_at_me = event.is_tome()

    # 1. Permission Checks
    if await is_blacklisted(user_id):
        return

    group_enabled, last_reply_time = await get_group_setting(group_id)
    if not group_enabled:
        return # If disabled, do not process further

    # 2. Trigger Conditions
    triggered = False
    current_time = int(time.time())

    # @ Trigger
    if is_at_me and message_text: # Ensure it's an @ and has actual content
        triggered = True

    # Random Trigger
    elif plugin_config.base_reply_probability > 0:
        time_since_last_reply = current_time - last_reply_time
        if time_since_last_reply >= plugin_config.min_reply_interval:
            if random.random() < plugin_config.base_reply_probability:
                triggered = True

    if not triggered:
        return

    # --- Subsequent processing logic ---
    message_history: List[Dict[str, Any]] = [] # Initialize empty list
    try:
        message_history = await get_message_history(bot, group_id, CONTEXT_LENGTH)
        # Ensure current message is included if history fetching fails or is empty
        if not message_history:
             sender_info = {"nickname": event.sender.nickname or user_id, "user_id": user_id}
             message_history = [{"user_id": user_id, "sender": sender_info, "message": message_text, "time": current_time}]
        elif len(message_history) < CONTEXT_LENGTH:
             sender_info = {"nickname": event.sender.nickname or user_id, "user_id": user_id}
             message_history.append({"user_id": user_id, "sender": sender_info, "message": message_text, "time": current_time})
    except Exception as e:
        print(f"AI Chat Plugin: Error getting message history for group {group_id}: {e}")
        await matcher.send("抱歉，获取聊天记录时出错，无法生成回复。")
        return

    # --- Build Prompt ---
    try:
        prompt = await build_prompt(message_history)
        if not prompt:
            if plugin_config: # Only send error if config was loaded
                 await matcher.send("抱歉，构建请求时出错，无法生成回复。")
            return
    except Exception as e:
        print(f"AI Chat Plugin: Error building prompt for group {group_id}: {e}")
        await matcher.send("抱歉，构建请求时出错，无法生成回复。")
        return

    # --- Call AI API ---
    ai_response = None # Initialize response variable
    if not plugin_config or not plugin_config.api_url or not plugin_config.api_key:
        print("AI Chat Plugin: Error - API URL or Key not configured.")
        await matcher.send("抱歉，AI 服务未正确配置，无法生成回复。")
        return

    try:
        system_content = plugin_config.system_prompt
        user_content_full = prompt.split("<user:", 1)[1].rsplit(">", 1)[0]
    except IndexError:
         print(f"AI Chat Plugin: Error parsing prompt structure for group {group_id}.")
         await matcher.send("抱歉，处理请求格式时出错，无法生成回复。")
         return

    headers = {
        "Authorization": f"Bearer {plugin_config.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": plugin_config.chat_model,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content_full}
        ],
        "max_tokens": plugin_config.max_tokens,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                plugin_config.api_url,
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()

            result = response.json()
            if result.get("choices") and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                ai_response = message.get("content")
                if ai_response:
                     ai_response = ai_response.strip()
                else:
                    ai_response = "抱歉，AI 没有返回有效内容。"
            else:
                print(f"AI Chat Plugin: Error - Unexpected API response structure for group {group_id}")
                ai_response = "抱歉，收到了来自 AI 的意外响应。"

    except httpx.TimeoutException:
        print(f"AI Chat Plugin: Error - Request to AI API timed out for group {group_id}.")
        await matcher.send("抱歉，连接 AI 服务超时，请稍后再试。")
        return
    except httpx.RequestError as e:
        print(f"AI Chat Plugin: Error - Network error calling AI API for group {group_id}: {e}")
        await matcher.send("抱歉，连接 AI 服务时发生网络错误。")
        return
    except httpx.HTTPStatusError as e:
        print(f"AI Chat Plugin: Error code: {e.response.status_code}")
        error_message = f"抱歉，AI 服务返回错误 ({e.response.status_code})。"
        await matcher.send(error_message)
        return
    except Exception as e:
        print(f"AI Chat Plugin: Error - Unexpected error during AI API call for group {group_id}: {e}")
        await matcher.send("抱歉，与 AI 服务交互时发生未知错误。")
        return

    # --- Send Reply ---
    try:
        if ai_response:
            await matcher.send(ai_response)
            await update_group_last_reply_time(group_id)
    except Exception as e:
        print(f"AI Chat Plugin: Error - Failed to send message to group {group_id}: {e}")

    # --- Impression Generation Logic ---
    if ai_response and not ai_response.startswith("抱歉"):
        try:
            bot_self_id = bot.self_id
            users_to_update: Dict[str, List[str]] = {}
            message_counts: Dict[str, int] = {}
            for record in message_history:
                 uid = record.get("user_id")
                 msg = record.get("message")
                 if uid and msg and uid != bot_self_id:
                     message_counts[uid] = message_counts.get(uid, 0) + 1
                     if uid not in users_to_update:
                         users_to_update[uid] = []
                     users_to_update[uid].append(msg)

            eligible_users = {
                uid for uid, count in message_counts.items()
                if count >= IMPRESSION_MIN_MESSAGES and uid != bot_self_id
            }

            for target_user_id in eligible_users:
                user_messages = users_to_update.get(target_user_id, [])
                if not user_messages: continue

                impression_prompt = await build_impression_prompt(target_user_id, user_messages)
                if not impression_prompt:
                    continue

                new_impression = None
                impression_payload = {
                    "model": plugin_config.impression_model,
                    "messages": [{"role": "user", "content": impression_prompt}],
                    "max_tokens": 150,
                    "temperature": 0.6,
                }
                try:
                    async with httpx.AsyncClient() as client:
                        impression_response = await client.post(
                            plugin_config.api_url,
                            headers=headers,
                            json=impression_payload,
                            timeout=45.0
                        )
                        impression_response.raise_for_status()
                        impression_result = impression_response.json()

                        if impression_result.get("choices") and len(impression_result["choices"]) > 0:
                            message = impression_result["choices"][0].get("message", {})
                            new_impression = message.get("content")
                            if new_impression:
                                new_impression = new_impression.strip()
                        else:
                            print(f"AI Chat Plugin: Error - Unexpected API response structure for impression generation (user {target_user_id})")

                except httpx.TimeoutException:
                    print(f"AI Chat Plugin: Error - Impression generation request timed out for user {target_user_id}.")
                except httpx.RequestError as e:
                    print(f"AI Chat Plugin: Error - Network error during impression generation for user {target_user_id}: {e}")
                except httpx.HTTPStatusError as e:
                    print(f"AI Chat Plugin: Impression generation Error code: {e.response.status_code} for user {target_user_id}")
                except Exception as e:
                    print(f"AI Chat Plugin: Error - Unexpected error during impression generation for user {target_user_id}: {e}")

                if not new_impression:
                    continue

                try:
                    await update_impression(target_user_id, new_impression)
                except Exception as e:
                    # Error logged in data_source.py
                    pass

        except Exception as e:
            print(f"AI Chat Plugin: Error during overall impression generation process for group {group_id}: {e}")


# --- Admin Commands ---
ai_chat_admin = on_command("ai_chat", aliases={"aichat"}, permission=SUPERUSER, priority=10, block=True)

@ai_chat_admin.handle()
async def handle_admin_command(bot: Bot, event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    """Handles administrative commands for the AI chat plugin."""
    arg_text = args.extract_plain_text().strip().lower()
    parts = arg_text.split()
    command = parts[0] if parts else ""
    params = parts[1:]

    if not isinstance(event, GroupMessageEvent):
         await matcher.send("Admin commands must be used in a group chat.")
         return
    group_id = str(event.group_id)

    if command == "group":
        if len(params) == 1:
            sub_command = params[0]
            if sub_command == "enable":
                await update_group_enabled(group_id, True)
                await matcher.send(f"AI chat feature enabled for this group.")
            elif sub_command == "disable":
                await update_group_enabled(group_id, False)
                await matcher.send(f"AI chat feature disabled for this group.")
            else:
                await matcher.send("Invalid group sub-command. Use 'enable' or 'disable'.")
        else:
            await matcher.send("Usage: /ai_chat group enable|disable")

    elif command == "blacklist":
        if len(params) == 2:
            sub_command = params[0]
            target_qq = params[1]
            if not target_qq.isdigit():
                await matcher.send("Invalid QQ number.")
                return

            if sub_command == "add":
                await add_to_blacklist(target_qq)
                await matcher.send(f"QQ {target_qq} added to blacklist.")
            elif sub_command == "remove":
                await remove_from_blacklist(target_qq)
                await matcher.send(f"QQ {target_qq} removed from blacklist.")
            else:
                await matcher.send("Invalid blacklist sub-command. Use 'add' or 'remove'.")
        else:
            await matcher.send("Usage: /ai_chat blacklist add|remove <QQ Number>")

    else:
        usage_text = (
            "AI Chat Admin Commands:\n"
            "/ai_chat group enable|disable - Toggle AI for the current group\n"
            "/ai_chat blacklist add|remove <QQ Number> - Manage user blacklist (SUPERUSER only)"
        )
        await matcher.send(usage_text)