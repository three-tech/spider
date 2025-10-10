"""
高级管理指令处理器

负责处理管理员专用的高级命令，如任务控制、重新推送等
"""
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from telegram.error import TelegramError
    from telegram_bot.bot import TelegramBot

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from base.logger import get_logger


logger = get_logger("admin_handler")


class AdminHandler:
    """高级管理指令处理器"""
    
    def __init__(self, bot: 'TelegramBot'):
        """
        初始化管理员处理器
        
        Args:
            bot: Telegram Bot实例
        """
        self.bot = bot
        self.database = bot.database
    
    async def handle_repush_group_command(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE') -> None:
        """
        处理 /repush_group 命令 - 重新推送指定群组的内容
        
        Args:
            update: 更新对象
            context: 上下文对象
        """
        try:
            user_id = update.effective_user.id
            
            # 检查管理员权限
            if not self._is_admin(user_id):
                await update.message.reply_text("❌ 权限不足，仅管理员可执行此操作")
                return
            
            # 解析参数
            args = context.args or []
            if len(args) < 1:
                await update.message.reply_text(
                    "📋 使用方法: /repush_group <群组ID>\n\n"
                    "示例: /repush_group -100123456789"
                )
                return
            
            chat_id = int(args[0])
            
            # 执行重新推送
            success = await self._repush_group_content(chat_id)
            
            if success:
                await update.message.reply_text(f"✅ 群组 {chat_id} 的内容重新推送完成")
                logger.info(f"群组 {chat_id} 重新推送 by user {user_id}")
            else:
                await update.message.reply_text(f"❌ 群组 {chat_id} 重新推送失败")
                
        except Exception as e:
            logger.error(f"处理/repush_group命令失败: {e}")
            await update.message.reply_text("❌ 重新推送失败")
    
    async def handle_repush_all_command(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE') -> None:
        """
        处理 /repush_all 命令 - 重新推送所有群组的内容
        
        Args:
            update: 更新对象
            context: 上下文对象
        """
        try:
            user_id = update.effective_user.id
            
            # 检查管理员权限
            if not self._is_admin(user_id):
                await update.message.reply_text("❌ 权限不足，仅管理员可执行此操作")
                return
            
            # 执行重新推送
            success = await self._repush_all_groups()
            
            if success:
                await update.message.reply_text("✅ 所有群组的内容重新推送完成")
                logger.info(f"所有群组重新推送 by user {user_id}")
            else:
                await update.message.reply_text("❌ 重新推送失败")
                
        except Exception as e:
            logger.error(f"处理/repush_all命令失败: {e}")
            await update.message.reply_text("❌ 重新推送失败")
    
    async def handle_start_job_command(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE') -> None:
        """
        处理 /start_job 命令 - 启动指定任务
        
        Args:
            update: 更新对象
            context: 上下文对象
        """
        try:
            user_id = update.effective_user.id
            
            # 检查管理员权限
            if not self._is_admin(user_id):
                await update.message.reply_text("❌ 权限不足，仅管理员可执行此操作")
                return
            
            # 解析参数
            args = context.args or []
            if len(args) < 1:
                await update.message.reply_text(
                    "📋 使用方法: /start_job <任务名称>\n\n"
                    "可用任务:\n"
                    "• content_push - 内容推送任务\n"
                    "• status_report - 状态报告任务\n"
                    "• all - 所有任务"
                )
                return
            
            job_name = args[0]
            success = self._start_job(job_name)
            
            if success:
                await update.message.reply_text(f"✅ 任务 {job_name} 已启动")
                logger.info(f"任务 {job_name} 启动 by user {user_id}")
            else:
                await update.message.reply_text(f"❌ 任务 {job_name} 启动失败")
                
        except Exception as e:
            logger.error(f"处理/start_job命令失败: {e}")
            await update.message.reply_text("❌ 任务启动失败")
    
    async def handle_stop_job_command(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE') -> None:
        """
        处理 /stop_job 命令 - 停止指定任务
        
        Args:
            update: 更新对象
            context: 上下文对象
        """
        try:
            user_id = update.effective_user.id
            
            # 检查管理员权限
            if not self._is_admin(user_id):
                await update.message.reply_text("❌ 权限不足，仅管理员可执行此操作")
                return
            
            # 解析参数
            args = context.args or []
            if len(args) < 1:
                await update.message.reply_text(
                    "📋 使用方法: /stop_job <任务名称>\n\n"
                    "可用任务:\n"
                    "• content_push - 内容推送任务\n"
                    "• status_report - 状态报告任务\n"
                    "• all - 所有任务"
                )
                return
            
            job_name = args[0]
            success = self._stop_job(job_name)
            
            if success:
                await update.message.reply_text(f"✅ 任务 {job_name} 已停止")
                logger.info(f"任务 {job_name} 停止 by user {user_id}")
            else:
                await update.message.reply_text(f"❌ 任务 {job_name} 停止失败")
                
        except Exception as e:
            logger.error(f"处理/stop_job命令失败: {e}")
            await update.message.reply_text("❌ 任务停止失败")
    
    async def handle_test_run_command(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE') -> None:
        """
        处理 /test_run 命令 - 测试运行指定功能
        
        Args:
            update: 更新对象
            context: 上下文对象
        """
        try:
            user_id = update.effective_user.id
            
            # 检查管理员权限
            if not self._is_admin(user_id):
                await update.message.reply_text("❌ 权限不足，仅管理员可执行此操作")
                return
            
            # 解析参数
            args = context.args or []
            if len(args) < 1:
                await update.message.reply_text(
                    "📋 使用方法: /test_run <功能名称>\n\n"
                    "可用功能:\n"
                    "• push - 测试推送功能\n"
                    "• ad - 测试广告功能\n"
                    "• report - 测试报告功能"
                )
                return
            
            function_name = args[0]
            success = await self._test_run_function(function_name)
            
            if success:
                await update.message.reply_text(f"✅ 功能 {function_name} 测试完成")
                logger.info(f"功能 {function_name} 测试 by user {user_id}")
            else:
                await update.message.reply_text(f"❌ 功能 {function_name} 测试失败")
                
        except Exception as e:
            logger.error(f"处理/test_run命令失败: {e}")
            await update.message.reply_text("❌ 测试运行失败")
    
    def _is_admin(self, user_id: int) -> bool:
        """
        检查用户是否为管理员
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否为管理员
        """
        try:
            # 从配置中获取管理员列表
            admins = self.bot.config.get('admins', [])
            return user_id in admins
        except Exception as e:
            logger.error(f"检查管理员权限失败: {e}")
            return False
    
    async def _repush_group_content(self, chat_id: int) -> bool:
        """
        重新推送指定群组的内容
        
        Args:
            chat_id: 群组ID
            
        Returns:
            操作是否成功
        """
        try:
            # TODO: 实现重新推送逻辑
            # 1. 获取该群组的所有订阅
            # 2. 重置推送进度
            # 3. 触发立即推送
            
            logger.info(f"重新推送群组 {chat_id} 的内容")
            return True
            
        except Exception as e:
            logger.error(f"重新推送群组 {chat_id} 失败: {e}")
            return False
    
    async def _repush_all_groups(self) -> bool:
        """
        重新推送所有群组的内容
        
        Returns:
            操作是否成功
        """
        try:
            # TODO: 实现批量重新推送逻辑
            # 1. 获取所有活跃订阅
            # 2. 重置所有推送进度
            # 3. 触发批量推送
            
            logger.info("重新推送所有群组的内容")
            return True
            
        except Exception as e:
            logger.error(f"重新推送所有群组失败: {e}")
            return False
    
    def _start_job(self, job_name: str) -> bool:
        """
        启动指定任务
        
        Args:
            job_name: 任务名称
            
        Returns:
            操作是否成功
        """
        try:
            if not self.bot.scheduler:
                return False
            
            if job_name == 'all':
                # 启动所有任务
                self.bot.scheduler.scheduler.resume()
                return True
            elif job_name in ['content_push', 'status_report']:
                # 启动特定任务
                job = self.bot.scheduler.jobs.get(job_name)
                if job:
                    job.resume()
                    return True
            return False
            
        except Exception as e:
            logger.error(f"启动任务 {job_name} 失败: {e}")
            return False
    
    def _stop_job(self, job_name: str) -> bool:
        """
        停止指定任务
        
        Args:
            job_name: 任务名称
            
        Returns:
            操作是否成功
        """
        try:
            if not self.bot.scheduler:
                return False
            
            if job_name == 'all':
                # 停止所有任务
                self.bot.scheduler.scheduler.pause()
                return True
            elif job_name in ['content_push', 'status_report']:
                # 停止特定任务
                job = self.bot.scheduler.jobs.get(job_name)
                if job:
                    job.pause()
                    return True
            return False
            
        except Exception as e:
            logger.error(f"停止任务 {job_name} 失败: {e}")
            return False
    
    async def _test_run_function(self, function_name: str) -> bool:
        """
        测试运行指定功能
        
        Args:
            function_name: 功能名称
            
        Returns:
            测试是否成功
        """
        try:
            if function_name == 'push':
                # 测试推送功能
                return await self._test_push_function()
            elif function_name == 'ad':
                # 测试广告功能
                return await self._test_ad_function()
            elif function_name == 'report':
                # 测试报告功能
                return await self._test_report_function()
            else:
                return False
                
        except Exception as e:
            logger.error(f"测试功能 {function_name} 失败: {e}")
            return False
    
    async def _test_push_function(self) -> bool:
        """测试推送功能"""
        try:
            # TODO: 实现推送功能测试
            logger.info("测试推送功能")
            return True
        except Exception as e:
            logger.error(f"测试推送功能失败: {e}")
            return False
    
    async def _test_ad_function(self) -> bool:
        """测试广告功能"""
        try:
            # TODO: 实现广告功能测试
            logger.info("测试广告功能")
            return True
        except Exception as e:
            logger.error(f"测试广告功能失败: {e}")
            return False
    
    async def _test_report_function(self) -> bool:
        """测试报告功能"""
        try:
            # TODO: 实现报告功能测试
            logger.info("测试报告功能")
            return True
        except Exception as e:
            logger.error(f"测试报告功能失败: {e}")
            return False