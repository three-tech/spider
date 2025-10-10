"""
Telegram Bot 主程序入口

负责整合所有模块并启动机器人服务
"""
import os
import signal
import sys
from typing import Optional

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from base.logger import get_logger

from telegram_bot.bot import TelegramBot
from telegram_bot.scheduler import TelegramScheduler
from telegram_bot.database import TelegramDatabaseManager

logger = get_logger("telegram_main")


class TelegramBotService:
    """Telegram Bot 服务管理器"""

    def __init__(self):
        """
        初始化服务管理器
        """
        self.bot: Optional[TelegramBot] = None
        self.scheduler: Optional[TelegramScheduler] = None
        self.db_manager: Optional[TelegramDatabaseManager] = None
        self.is_running = False

    def initialize_database(self) -> bool:
        """
        初始化数据库连接
        
        Returns:
            初始化是否成功
        """
        try:
            self.db_manager = TelegramDatabaseManager()
            self.db_manager.init_database()
            logger.info("✅ 数据库初始化成功")
            return True
        except Exception as error:
            logger.error(f"❌ 数据库初始化失败: {error}")
            return False

    def initialize_bot(self) -> bool:
        """
        初始化Telegram Bot
        
        Returns:
            初始化是否成功
        """
        try:
            telegram_config = self.config.get('telegram_bot', {})
            self.bot = TelegramBot(telegram_config, self.db_manager)
            logger.info("✅ Telegram Bot初始化成功")
            return True
        except Exception as error:
            logger.error(f"❌ Telegram Bot初始化失败: {error}")
            return False

    def initialize_scheduler(self) -> bool:
        """
        初始化任务调度器
        
        Returns:
            初始化是否成功
        """
        try:
            self.scheduler = TelegramScheduler(self.db_manager)
            logger.info("✅ 任务调度器初始化成功")
            return True
        except Exception as error:
            logger.error(f"❌ 任务调度器初始化失败: {error}")
            return False

    def setup_signal_handlers(self):
        """设置信号处理器"""

        def signal_handler(signum, frame):
            logger.info(f"📡 收到信号 {signum}，正在优雅关闭...")
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def start(self):
        """
        启动Telegram Bot服务（同步方法）
        """
        logger.info("🚀 正在启动Telegram Bot服务...")

        try:
            # 1. 直接创建Bot实例（Bot会从数据库读取配置）
            self.bot = TelegramBot()

            # 2. 初始化调度器
            self.scheduler = TelegramScheduler(self.bot.database)

            # 3. 设置调度器到Bot
            self.bot.set_scheduler(self.scheduler)

            # 4. 设置信号处理器
            self.setup_signal_handlers()

            # 5. 启动Bot
            self.is_running = True
            logger.info("✅ 所有组件初始化完成，正在启动Bot...")

            # 启动Bot（这会阻塞运行，调度器将在Bot内部启动）
            self.bot.start()

        except Exception as error:
            logger.error(f"❌ Bot启动失败: {error}")
            self.stop()

    def stop(self):
        """
        停止Telegram Bot服务
        """
        if not self.is_running:
            return

        logger.info("🛑 正在停止Telegram Bot服务...")
        self.is_running = False

        try:
            # 停止调度器
            if self.scheduler:
                self.scheduler.stop()

            # 停止Bot
            if self.bot:
                self.bot.stop()

            logger.info("✅ Telegram Bot服务已停止")

        except Exception as error:
            logger.error(f"❌ 服务停止过程中发生错误: {error}")
        finally:
            sys.exit(0)


def main():
    """
    主函数 - 使用简单的阻塞方式启动
    """
    service = TelegramBotService()

    # 使用简单的阻塞方式启动
    try:
        # 直接启动服务（同步方法）
        service.start()

    except KeyboardInterrupt:
        print("👋 用户中断，服务已停止")
    except Exception as error:
        print(f"❌ 服务运行异常: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
