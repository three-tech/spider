"""
Telegram机器人核心类

负责协调应用、数据库、调度器和命令处理器的核心逻辑
"""
import os
import sys
from typing import Dict, Any, TYPE_CHECKING

from telegram.ext import Application

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.logger import get_logger
from telegram_bot.database import TelegramDatabaseManager

# 类型检查导入，避免循环依赖
if TYPE_CHECKING:
    from telegram_bot.scheduler import TelegramScheduler


class TelegramBot:
    """Telegram机器人主类"""

    def __init__(self, bot_token: str = None, telegram_config: Dict[str, Any] = None):
        """
        初始化机器人
        
        Args:
            bot_token: Telegram机器人API令牌（可选，如果为None则从数据库读取）
            telegram_config: Telegram相关配置（可选，如果为None则从数据库读取）
        """
        self.logger = get_logger(self.__class__.__name__)

        # 如果提供了配置，使用提供的值；否则从数据库读取
        if bot_token and telegram_config:
            self.token = bot_token
            self.config = telegram_config
        else:
            # 从数据库读取配置
            self._load_config_from_database()

        self.application = self._create_application(self.token)
        self.database = TelegramDatabaseManager(self.config)
        self.scheduler = None  # 延迟初始化

    def _load_config_from_database(self) -> None:
        """
        从数据库加载配置
        
        从telegram_settings表中读取bot_token和target_group配置
        """
        try:
            # 初始化数据库连接（临时创建实例来读取配置）
            from telegram_bot.database import TelegramDatabaseManager
            temp_db = TelegramDatabaseManager({})

            # 读取bot配置
            bot_settings = temp_db.get_settings_by_type("bot_config")
            if not bot_settings:
                raise ValueError("未在数据库中找到bot配置")

            # 解析配置
            bot_config = bot_settings[0]  # 取第一个配置
            self.token = bot_config.get("bot_token")
            self.config = {
                "target_group": bot_config.get("target_group", "@imok911"),
                "database": {
                    "host": "localhost",
                    "port": 3306,
                    "user": "root",
                    "password": "123456",
                    "database": "resource"
                }
            }

            self.logger.info("✅ 从数据库成功加载配置")

        except Exception as e:
            self.logger.error(f"❌ 从数据库加载配置失败: {e}")
            raise

    def _create_application(self, token: str) -> Application:
        """
        创建并配置Telegram应用实例
        
        Args:
            token: 机器人令牌
            
        Returns:
            配置好的Application实例
        """
        self.logger.info("正在创建Telegram应用实例...")
        application = Application.builder().token(token).build()
        self.logger.info("✅ Telegram应用实例创建完成")
        return application

    def set_scheduler(self, scheduler: 'TelegramScheduler') -> None:
        """设置调度器实例（依赖注入）"""
        self.scheduler = scheduler

    def setup(self) -> None:
        """设置机器人所有组件"""
        self.logger.info("正在设置机器人组件...")

        # 1. 初始化数据库并创建必要表
        self.database.init_database()
        self.logger.info("✅ 数据库初始化完成")

        # 2. 设置命令和消息处理器（延迟导入）
        self._setup_handlers()
        self.logger.info("✅ 处理器设置完成")

        # 3. 规划调度器任务（但不启动调度器）
        if self.scheduler:
            self.scheduler.schedule_jobs()
            self.logger.info("✅ 调度器任务规划完成")
        else:
            self.logger.warning("⚠️ 调度器未设置，跳过任务规划")

    def _setup_handlers(self) -> None:
        """延迟导入并设置处理器"""
        # 延迟导入避免循环依赖
        from telegram_bot.handlers import setup_handlers
        handlers = setup_handlers(self.application, self)

        # 设置bot实例到alert_handler
        handlers['alert_handler'].bot_instance = self

    def start(self) -> None:
        """启动机器人（同步方法）"""
        try:
            # 1. 设置机器人组件（但不启动调度器）
            self.setup()

            # 2. 启动调度器（如果已设置）
            if self.scheduler:
                # 调度器在setup()方法中已经规划了任务，这里只需要启动
                self.logger.info("正在启动调度器...")
                self.scheduler.start()

            # 3. 使用简单的阻塞方式启动Bot
            self.logger.info("🚀 机器人开始轮询...")

            # 使用run_polling()方法，这是Telegram Bot的标准启动方式
            self.application.run_polling()

        except Exception as error:
            self.logger.error(f"❌ Bot启动失败: {error}")
            raise
        finally:
            # 确保资源清理
            if self.scheduler:
                self.scheduler.stop()

    def stop(self) -> None:
        """停止机器人"""
        try:
            if hasattr(self, 'application') and self.application.running:
                self.application.stop()
                self.logger.info("✅ Bot已停止")
        except Exception as error:
            self.logger.error(f"❌ Bot停止失败: {error}")
