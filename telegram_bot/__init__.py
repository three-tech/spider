"""
Telegram Bot Module

一个基于Python-Telegram-Bot框架的内容推送机器人，
负责将资源内容自动推送到订阅的Telegram群组。
"""

__version__ = "1.0.0"
__author__ = "Spider Team"
__description__ = "Telegram内容推送机器人"

# 避免循环导入，只导出类型提示
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram.bot import TelegramBot
    from telegram.database import TelegramDatabaseManager
    from telegram.scheduler import TelegramScheduler

__all__ = [
    "TelegramBot",
    "TelegramDatabaseManager",
    "TelegramScheduler"
]