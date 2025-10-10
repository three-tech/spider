"""
Telegram Bot 处理器模块

包含所有命令和消息处理器
"""
import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from telegram_bot.handlers.summary_handler import SummaryHandler
from telegram_bot.handlers.alert_handler import AlertHandler
from telegram_bot.handlers.report_handler import ReportHandler
from telegram_bot.handlers.ad_handler import AdHandler
from telegram_bot.handlers.admin_handler import AdminHandler

def setup_handlers(application, bot):
    """设置所有处理器到应用"""
    from telegram_bot.database import TelegramDatabaseManager
    from telegram.ext import CommandHandler, MessageHandler, filters
    
    db_manager = TelegramDatabaseManager(bot.config)
    
    # 创建基础处理器
    summary_handler = SummaryHandler(db_manager=db_manager)
    alert_handler = AlertHandler(db_manager=db_manager)
    ad_handler = AdHandler(bot=bot)
    admin_handler = AdminHandler(bot=bot)
    
    # 创建ReportHandler（服务类，不注册到应用）
    report_handler = ReportHandler(summary_handler=summary_handler, alert_handler=alert_handler)
    
    # 添加基础指令处理器
    async def start_command(update, context):
        """处理 /start 指令"""
        await update.message.reply_text(
            "🤖 欢迎使用资源推送机器人！\n\n"
            "可用指令：\n"
            "/help - 查看帮助信息\n"
            "/status - 查看系统状态\n"
            "/summary - 查看统计报告（管理员）"
        )
    
    async def help_command(update, context):
        """处理 /help 指令"""
        await update.message.reply_text(
            "📋 帮助信息\n\n"
            "基础指令：\n"
            "/start - 启动机器人\n"
            "/help - 查看帮助\n"
            "/status - 系统状态\n\n"
            "管理指令（管理员）：\n"
            "/summary - 统计报告\n"
            "/repush_group - 重新推送群组\n"
            "/repush_all - 重新推送所有\n"
            "/start_job - 启动任务\n"
            "/stop_job - 停止任务\n"
            "/test_run - 测试运行"
        )
    
    async def status_command(update, context):
        """处理 /status 指令"""
        await update.message.reply_text(
            "✅ 系统状态正常\n"
            "🤖 Bot正在运行\n"
            "🔄 持续监控中..."
        )
    
    # 注册基础指令处理器
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # 注册处理器到应用
    application.add_handler(summary_handler.get_handler())
    
    # 为AdHandler创建消息处理器（处理转发消息）
    application.add_handler(MessageHandler(filters.FORWARDED, ad_handler.handle_forwarded_message))
    
    # 为AdminHandler创建命令处理器
    application.add_handler(CommandHandler("repush_group", admin_handler.handle_repush_group_command))
    application.add_handler(CommandHandler("repush_all", admin_handler.handle_repush_all_command))
    application.add_handler(CommandHandler("start_job", admin_handler.handle_start_job_command))
    application.add_handler(CommandHandler("stop_job", admin_handler.handle_stop_job_command))
    application.add_handler(CommandHandler("test_run", admin_handler.handle_test_run_command))
    
    # 返回所有处理器实例，包括服务类
    return {
        'summary_handler': summary_handler,
        'alert_handler': alert_handler,
        'report_handler': report_handler,
        'ad_handler': ad_handler,
        'admin_handler': admin_handler
    }

__all__ = [
    'SummaryHandler',
    'AlertHandler', 
    'ReportHandler',
    'AdHandler',
    'AdminHandler',
    'setup_handlers'
]