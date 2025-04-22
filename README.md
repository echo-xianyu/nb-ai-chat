# NoneBot Plugin: AI Chat Assistant

一个基于 NoneBot2 和 OneBot V11 标准的 QQ 群聊 AI 助手插件。
大部分代码由AI生成，完全自用。

## 功能特性

*   **AI 聊天:** 集成 OpenAI 兼容的 API，可在 QQ 群聊中与 AI 进行对话。
*   **上下文理解:** 尝试获取最近的群聊消息作为上下文，让 AI 的回复更连贯。
*   **用户印象:**
    *   根据用户在上下文中的发言频率，自动触发 AI 生成用户印象（需 AI 回复成功后）。
    *   印象会存储在数据库中，并在后续对话中提供给 AI，以实现更个性化的回复。
    *   生成印象的 Prompt 可在配置文件中自定义。
*   **灵活触发:**
    *   通过 `@机器人` 显式触发对话。
    *   根据配置的概率和时间间隔进行随机回复。
*   **配置管理:**
    *   所有关键参数（API 地址、Key、Prompt、触发概率、间隔、Token 限制等）均可通过 `data/AI_chat/config.yaml` 文件配置。
    *   首次运行插件时会自动生成带注释的示例配置文件。
*   **群组管理:**
    *   可通过命令启用/禁用特定群聊的 AI 功能。
*   **用户管理:**
    *   可通过命令将特定 QQ 用户加入/移出黑名单，阻止其触发 AI。
*   **数据库存储:** 使用 SQLite 存储用户印象、黑名单和群聊设置，数据持久化。

## 安装

1.  **环境准备:** 确保您已正确安装并配置了 NoneBot2 和 OneBot V11 适配器（如 `nonebot-adapter-onebot`）。
2.  **放置插件:** 将 `ai_chat` 文件夹整个放入您 NoneBot 项目配置的插件目录。
3.  **安装依赖:** 在您的 NoneBot 项目虚拟环境中，确保安装了以下依赖库：
    ```bash
    pip install nonebot2 nonebot-adapter-onebot pyyaml aiosqlite httpx pydantic
    ```
    *   `nonebot2`, `nonebot-adapter-onebot`, `httpx`, `pydantic` 通常是 NoneBot 项目的基础依赖。
    *   `pyyaml` 用于解析配置文件。
    *   `aiosqlite` 用于异步操作 SQLite 数据库。
      
4.  **修改配置:** 修改pyproject.toml，添加ai_chat到plugins。

## 配置

1.  **首次运行:** 启动您的 NoneBot 项目。插件在首次加载时，如果发现 `data/AI_chat/config.yaml` 文件不存在，会自动创建该目录和文件，并填入默认配置和注释。同时，程序会因缺少有效 `api_key` 而在日志中报错并提示您修改配置。
2.  **编辑配置:** 打开 `data/AI_chat/config.yaml` 文件。
    *   **`api_key` (必需):** **务必**将 `api_key` 的值修改为您有效的 OpenAI 兼容 API 的 Key。
    *   **`api_url` (可选):** 如果您使用的不是标准的 OpenAI API 地址，请修改此项。
    *   **`system_prompt` (可选):** 修改 AI 的系统级提示词。
    *   **`impression_prompt` (可选):** 修改用于让 AI 生成用户印象的 Prompt 模板。注意保留 `{previous_impression}` 和 `{user_messages}` 两个占位符。
    *   **`base_reply_probability` (可选):** 调整随机回复的基础概率（0.0 到 1.0）。设为 0 可禁用随机回复。
    *   **`min_reply_interval` (可选):** 调整随机回复的最小时间间隔（秒）。
    *   **`max_tokens` (可选):** 调整 AI 单次回复的最大 token 限制。
    *   **`chat_model` (可选):** 指定用于主聊天回复的 AI 模型名称（例如 "gpt-3.5-turbo", "gpt-4" 等）。默认为 "gpt-3.5-turbo"。
    *   **`impression_model` (可选):** 指定用于生成用户印象的 AI 模型名称。可以与 `chat_model` 相同，或使用更轻量/便宜的模型。默认为 "gpt-3.5-turbo"。
3.  **重启 Bot:** 修改配置后，需要重启您的 NoneBot 项目使配置生效。

## 使用方法

*   **AI 对话:**
    *   在群聊中 `@机器人 + 你的消息`。
    *   等待 AI 根据配置进行随机回复。
*   **管理命令 (需要 SUPERUSER 权限):**
    *   `/ai_chat group enable`: 在当前群聊启用 AI 功能。
    *   `/ai_chat group disable`: 在当前群聊禁用 AI 功能。
    *   `/ai_chat blacklist add <QQ号>`: 将指定 QQ 号添加到黑名单。
    *   `/ai_chat blacklist remove <QQ号>`: 将指定 QQ 号从黑名单移除。

## 重要提示：消息历史获取

*   本插件的核心功能之一是获取聊天上下文。代码中 (`utils.py` 的 `get_message_history` 函数) 已实现尝试通过 OneBot V11 的 `get_group_msg_history` API 来获取历史消息。
*   **兼容性:** 此 API 的可用性和行为**高度依赖**您所使用的 OneBot V11 实现端（如 go-cqhttp, NapCat, Lagrange.Core 等）。**请确保您的实现端支持此 API**。
*   **潜在问题:** 如果您的实现端不支持此 API，或者返回的数据格式与预期不符，历史消息获取可能会失败（插件会打印错误日志），导致 AI 仅能基于当前消息进行回复。
*   **解决方案:**
    1.  **确认实现端支持:** 查阅您使用的 OneBot V11 实现的文档，确认 `get_group_msg_history` 的支持情况和返回格式。
    2.  **修改代码:** 如有必要，您可能需要修改 `utils.py` 中 `get_message_history` 函数内对返回数据的处理逻辑，以适配您的实现端。
    3.  **使用数据存储插件:** 考虑使用如 `nonebot-plugin-datastore` 等插件来存储和查询消息历史，并相应修改 `get_message_history` 函数的实现。

## 故障排查

*   **插件未加载/报错:**
    *   检查 `data/AI_chat/config.yaml` 是否存在且格式正确，特别是 `api_key` 是否已填写。
    *   检查数据库文件 `data/AI_chat/database.db` 是否可读写（权限问题）。
*   **AI 无响应:**
    *   检查 NoneBot 日志中是否有 API 调用错误（网络错误、超时、认证失败、API 返回错误码等）。
    *   确认 `config.yaml` 中的 `api_url` 和 `api_key` 正确无误。
    *   检查 AI 服务本身是否可用。
    *   检查群聊是否被禁用 (`/ai_chat group enable`)。
    *   检查用户是否在黑名单中 (`/ai_chat blacklist remove <QQ号>`)。
*   **随机回复不触发:**
    *   检查 `config.yaml` 中的 `base_reply_probability` 是否大于 0。
    *   检查 `min_reply_interval` 设置的时间间隔是否已满足。
*   **印象不生成/更新:**
    *   印象生成只在 AI 成功回复后触发。
    *   检查日志中是否有印象生成相关的 AI API 调用错误。
    *   检查用户发言次数是否满足 `impression_min_messages`（默认为 5）。
    *   检查 `config.yaml` 中的 `impression_prompt` 模板是否正确。
