"""
Telegram机器人命令和消息处理器

负责处理用户交互，包括命令响应和消息处理
"""
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.error import TelegramError

import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.logger import get_logger
from telegram_bot.bot import TelegramBot
from telegram_bot.handlers.summary_handler import SummaryHandler
from telegram_bot.handlers.alert_handler import AlertHandler
from telegram_bot.handlers.report_handler import ReportHandler
from telegram_bot.handlers.ad_handler import AdHandler
from telegram_bot.handlers.admin_handler import AdminHandler


logger = get_logger("telegram_handlers")


def setup_handlers(application, bot: TelegramBot) -> None:
    """
    设置所有命令和消息处理器
    
    Args:
        application: Telegram应用实例
        bot: Telegram机器人实例
    """
    logger.info("正在设置命令处理器...")
    
    # 初始化处理器实例
    summary_handler = SummaryHandler(bot.database)
    alert_handler = AlertHandler(bot)
    report_handler = ReportHandler(bot)
    ad_handler = AdHandler(bot)
    admin_handler = AdminHandler(bot)
    
    # 基础命令处理器
    application.add_handler(CommandHandler("start", _handle_start_command))
    application.add_handler(CommandHandler("help", _handle_help_command))
    application.add_handler(CommandHandler("status", _handle_status_command))
    
    # A-3任务：监控、汇报与基础管理指令
    application.add_handler(summary_handler.get_handler())  # SummaryHandler使用get_handler()
    
    # A-4任务：广告系统与高级管理指令
    application.add_handler(CommandHandler("config_ad", ad_handler.handle_config_ad_command))
    application.add_handler(CommandHandler("stop_job", admin_handler.handle_stop_job_command))
    application.add_handler(CommandHandler("test_run", admin_handler.handle_test_run_command))
    application.add_handler(CommandHandler("repush_group", admin_handler.handle_repush_group_command))
    application.add_handler(CommandHandler("stop_job", admin_handler.handle_stop_job_command))
    application.add_handler(CommandHandler("test_run", admin_handler.handle_test_run_command))
    application.add_handler(CommandHandler("repush_group", admin_handler.handle_repush_group_command))
    
    # 广告消息处理器（处理转发的广告消息）
    application.add_handler(MessageHandler(filters.FORWARDED, ad_handler.handle_forwarded_message))
    
    # 消息处理器
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_text_message))
    
    logger.info("✅ 处理器设置完成")


async def _handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /start 命令
    
    Args:
        update: 更新对象
        context: 上下文对象
    """
    try:
        welcome_message = """
        🤖 欢迎使用内容推送机器人！
        
        我是您的智能内容助手，负责为您推送最新的资源内容。
        
        可用命令：
        /help - 查看帮助信息
        /status - 查看机器人状态
        
        如需订阅特定标签内容，请联系管理员配置。
        """
        
        await update.message.reply_text(welcome_message.strip())
        logger.info(f"用户 {update.effective_user.id} 启动了机器人")
        
    except TelegramError as error:
        logger.error(f"处理 /start 命令失败: {error}")


async def _handle_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /help 命令
    
    Args:
        update: 更新对象
        context: 上下文对象
    """
    try:
        help_message = """
        📚 帮助文档
        
        命令列表：
        /start - 启动机器人
        /help - 查看帮助信息
        /status - 查看机器人状态
        
        功能说明：
        • 机器人会自动推送订阅的内容到群组
        • 推送频率为每30分钟一次
        • 状态报告每天凌晨2点发送给管理员
        
        如需修改订阅或配置，请联系管理员。
        """
        
        await update.message.reply_text(help_message.strip())
        logger.info(f"用户 {update.effective_user.id} 查看了帮助")
        
    except TelegramError as error:
        logger.error(f"处理 /help 命令失败: {error}")


async def _handle_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /status 命令
    
    Args:
        update: 更新对象
        context: 上下文对象
    """
    try:
        # 检查用户权限（简单实现）
        user_id = update.effective_user.id
        
        # TODO: 从数据库检查用户是否为管理员
        # 暂时允许所有用户查看状态
        status_message = """
        📊 机器人状态
        
        功能状态：
        • 机器人: 运行中
        • 推送服务: 活跃
        • 调度器: 正常
        
        注意：详细状态报告仅对管理员开放。
        """
        
        await update.message.reply_text(status_message.strip())
        logger.info(f"用户 {user_id} 查看了状态")
        
    except TelegramError as error:
        logger.error(f"处理 /status 命令失败: {error}")


async def _handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理普通文本消息
    
    Args:
        update: 更新对象
        context: 上下文对象
    """
    try:
        message_text = update.message.text
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        logger.debug(f"收到来自用户 {user_id} 的消息: {message_text}")
        
        # 简单的关键词响应
        responses = {
            "hello": "👋 你好！我是内容推送机器人。",
            "hi": "👋 你好！需要帮助请使用 /help 命令。",
            "谢谢": "😊 不客气！随时为您服务。",
        }
        
        response = responses.get(message_text.lower().strip())
        if response:
            await update.message.reply_text(response)
        else:
            # 默认响应
            await update.message.reply_text("🤔 抱歉，我不理解这个命令。请使用 /help 查看可用命令。")
            
    except TelegramError as error:
        logger.error(f"处理文本消息失败: {error}")