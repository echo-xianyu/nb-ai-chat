from nonebot import get_driver
from nonebot.plugin import PluginMetadata

# 导入配置模块
from .config import plugin_config, Config
# 导入数据库模块
from .data_source import init_db
# 导入事件处理模块 (确保 handlers.py 中有响应器被注册)
from . import handlers

# --- 插件元数据 ---
__plugin_meta__ = PluginMetadata(
    name="AI 聊天插件",
    description="基于 OpenAI 兼容 API 的 QQ 群聊 AI 助手，支持上下文、用户印象和群管理。",
    usage="""
    指令:
    /ai_chat group enable/disable - 启用/禁用当前群聊 AI 功能 (管理员)
    /ai_chat blacklist add/remove <QQ号> - 添加/移除 QQ 黑名单 (超级用户)

    触发方式:
    1. @机器人 + 聊天内容
    2. 群内随机回复 (需满足配置的概率和间隔)
    """,
    type="application",
    homepage="https://github.com/example/nonebot_plugin_ai_chat", # 示例地址，可修改
    config=Config, # 关联配置类，以便 NoneBot 加载和验证
    supported_adapters={"~onebot.v11"}, # 明确支持 OneBot V11
)

# --- Initialization ---
driver = get_driver()

@driver.on_startup
async def _initialize():
    """
    Initialize database and check configuration on bot startup.
    """
    if not plugin_config:
        print(f"插件 {__plugin_meta__.name} 配置加载失败，将不会运行。请检查 data/AI_chat/config.yaml")
        # Consider raising an exception to prevent NoneBot from loading this plugin further
        return

    # Initialize database
    try:
        await init_db()
        print(f"插件 {__plugin_meta__.name} 数据库初始化完成。")
    except Exception as e:
        print(f"插件 {__plugin_meta__.name} 数据库初始化失败: {e}")
        # Decide whether to prevent plugin loading, e.g., by raising an exception
        # raise RuntimeError(f"Database initialization failed: {e}") from e
        return # Or just print the error and prevent the plugin from running

    print(f"插件 {__plugin_meta__.name} 初始化完成并加载成功。")