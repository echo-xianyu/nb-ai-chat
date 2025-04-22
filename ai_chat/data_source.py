import aiosqlite
from pathlib import Path
import asyncio
from typing import Optional, Tuple, List
import time

# --- 数据库文件路径 ---
DB_DIR = Path("data/AI_chat")
DB_PATH = DB_DIR / "database.db"

# --- 初始化数据库 ---
async def init_db():
    """
    初始化 SQLite 数据库并创建必要的表 (如果不存在)。
    """
    DB_DIR.mkdir(parents=True, exist_ok=True)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # 创建 impressions 表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS impressions (
                    qq_id TEXT PRIMARY KEY,
                    impression_text TEXT,
                    last_update INTEGER  -- 存储 Unix 时间戳
                )
            """)
            # 创建 blacklist 表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS blacklist (
                    qq_id TEXT PRIMARY KEY
                )
            """)
            # 创建 group_settings 表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS group_settings (
                    group_id TEXT PRIMARY KEY,
                    enabled BOOLEAN DEFAULT TRUE, -- 默认启用
                    last_reply_time INTEGER DEFAULT 0 -- 存储 Unix 时间戳
                )
            """)
            await db.commit()
        print(f"数据库 {DB_PATH} 初始化/连接成功。")
    except Exception as e:
        print(f"数据库 {DB_PATH} 初始化失败: {e}")
        raise # 抛出异常，以便上层处理

# --- 数据库操作函数 (后续将逐步实现具体逻辑) ---

# --- Impression 相关 ---
async def get_impression(qq_id: str) -> Optional[str]:
    """获取指定 QQ 的印象文本"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT impression_text FROM impressions WHERE qq_id = ?", (qq_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def update_impression(qq_id: str, impression_text: str):
    """更新或插入指定 QQ 的印象"""
    current_time = int(time.time())
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO impressions (qq_id, impression_text, last_update) VALUES (?, ?, ?)",
                (qq_id, impression_text, current_time)
            )
            await db.commit()
    except Exception as e:
        # Log error according to the requested format
        print(f"AI Chat Plugin: 在数据库 impressions 写入 {qq_id} 时出现错误，写入失败: {e}")
        # Re-raise the exception so the caller in handlers.py knows about the failure
        raise

# --- Blacklist 相关 ---
async def is_blacklisted(qq_id: str) -> bool:
    """检查 QQ 是否在黑名单中"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM blacklist WHERE qq_id = ?", (qq_id,)) as cursor:
            return await cursor.fetchone() is not None

async def add_to_blacklist(qq_id: str):
    """将 QQ 添加到黑名单"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO blacklist (qq_id) VALUES (?)", (qq_id,))
        await db.commit()

async def remove_from_blacklist(qq_id: str):
    """将 QQ 从黑名单移除"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM blacklist WHERE qq_id = ?", (qq_id,))
        await db.commit()

# --- Group Settings 相关 ---
async def get_group_setting(group_id: str) -> Tuple[bool, int]:
    """获取群聊设置 (enabled, last_reply_time)"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 尝试插入默认值，如果群聊不存在的话
        await db.execute(
            "INSERT OR IGNORE INTO group_settings (group_id) VALUES (?)",
            (group_id,)
        )
        await db.commit() # 确保插入生效
        # 查询设置
        async with db.execute("SELECT enabled, last_reply_time FROM group_settings WHERE group_id = ?", (group_id,)) as cursor:
            row = await cursor.fetchone()
            # row 不应该为 None，因为上面保证了插入
            return (bool(row[0]), row[1]) if row else (True, 0) # 提供默认值以防万一

async def update_group_enabled(group_id: str, enabled: bool):
    """更新群聊启用状态"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO group_settings (group_id, enabled, last_reply_time) VALUES (?, ?, COALESCE((SELECT last_reply_time FROM group_settings WHERE group_id = ?), 0))",
            (group_id, enabled, group_id) # 使用 COALESCE 保留旧的 last_reply_time
        )
        await db.commit()

async def update_group_last_reply_time(group_id: str):
    """更新群聊的最后回复时间"""
    current_time = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE group_settings SET last_reply_time = ? WHERE group_id = ?",
            (current_time, group_id)
        )
        # 如果群聊不存在（理论上不应该，因为 get_group_setting 会创建），此 UPDATE 无效
        # 可以考虑先 INSERT OR IGNORE 再 UPDATE，但 get_group_setting 已处理
        await db.commit()