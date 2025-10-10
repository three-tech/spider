"""
Telegram机器人调度器

负责管理定时任务，包括内容推送、状态报告等后台作业
"""
from typing import Dict, Any, TYPE_CHECKING
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.logger import get_logger

# 类型检查导入，避免循环依赖
if TYPE_CHECKING:
    from telegram_bot.bot import TelegramBot
    from telegram_bot.tasks import PushTask, HealthCheckTask


class TelegramScheduler:
    """Telegram机器人任务调度器"""
    
    def __init__(self, database_manager):
        """
        初始化调度器
        
        Args:
            database_manager: 数据库管理器实例
        """
        self.logger = get_logger(self.__class__.__name__)
        self.database_manager = database_manager
        self.scheduler = AsyncIOScheduler()
        self.jobs = {}
        self.bot = None

    def schedule_jobs(self) -> None:
        """规划所有定时任务（不启动调度器）"""
        self.logger.info("正在规划定时任务...")
        
        # 1. 内容推送任务 - 每30分钟执行一次
        self._schedule_content_push_job()
        
        # 2. 状态报告任务 - 每天凌晨2点执行
        self._schedule_status_report_job()
        
        self.logger.info("✅ 调度器任务规划完成")

    def _schedule_content_push_job(self) -> None:
        """规划内容推送任务"""
        try:
            job = self.scheduler.add_job(
                func=self._push_content_to_subscriptions,
                trigger=CronTrigger(minute="*/30"),  # 每30分钟
                id="content_push",
                name="内容推送任务",
                replace_existing=True
            )
            self.jobs["content_push"] = job
            self.logger.info("✅ 内容推送任务规划完成 (每30分钟)")
        except Exception as error:
            self.logger.error(f"规划内容推送任务失败: {error}", exc_info=True)

    def _schedule_status_report_job(self) -> None:
        """规划状态报告任务"""
        try:
            job = self.scheduler.add_job(
                func=self._send_status_report,
                trigger=CronTrigger(hour=2, minute=0),  # 每天凌晨2点
                id="status_report",
                name="状态报告任务",
                replace_existing=True
            )
            self.jobs["status_report"] = job
            self.logger.info("✅ 状态报告任务规划完成 (每天凌晨2点)")
        except Exception as error:
            self.logger.error(f"规划状态报告任务失败: {error}", exc_info=True)

    def _push_content_to_subscriptions(self) -> None:
        """
        推送内容到所有订阅的群组
        
        这是核心业务逻辑，根据订阅关系推送最新的内容
        """
        self.logger.info("开始执行内容推送任务...")
        
        try:
            # 检查Bot是否已设置
            if not hasattr(self, 'bot') or self.bot is None:
                self.logger.error("Bot未初始化，无法执行推送任务")
                return
            
            # 创建并执行推送任务
            push_task = PushTask(self.database_manager, self.bot)
            
            # 使用当前事件循环执行异步任务
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建新任务
                    asyncio.create_task(push_task.execute())
                else:
                    # 否则直接运行
                    result = loop.run_until_complete(push_task.execute())
                    self.logger.info(f"内容推送任务完成: {result}")
            except RuntimeError:
                # 如果没有事件循环，创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(push_task.execute())
                    self.logger.info(f"内容推送任务完成: {result}")
                finally:
                    loop.close()
            
        except Exception as error:
            self.logger.error(f"内容推送任务执行失败: {error}", exc_info=True)

    def _push_content_for_subscription(self, subscription) -> bool:
        """
        为单个订阅推送内容
        
        Args:
            subscription: 订阅记录对象
            
        Returns:
            推送是否成功
        """
        try:
            # TODO: 实现具体的内容推送逻辑
            # 1. 根据tag和last_resource_x_id查询新内容
            # 2. 格式化消息内容
            # 3. 发送到指定群组
            # 4. 更新推送进度
            
            self.logger.debug(f"推送内容到群组 {subscription.chat_id}, 标签: {subscription.tag}")
            return True
            
        except Exception as error:
            self.logger.error(f"推送内容到群组 {subscription.chat_id} 失败: {error}")
            return False

    def _send_status_report(self) -> None:
        """
        发送状态报告给管理员
        
        汇总机器人运行状态、订阅情况等关键指标
        """
        self.logger.info("开始生成状态报告...")
        
        try:
            # 检查Bot是否已设置
            if not hasattr(self, 'bot') or self.bot is None:
                self.logger.error("Bot未初始化，无法执行健康检查")
                return
            
            # 创建并执行健康检查任务
            health_task = HealthCheckTask(self.database_manager, self.bot)
            
            # 使用当前事件循环执行异步任务
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建新任务
                    asyncio.create_task(health_task.execute())
                else:
                    # 否则直接运行
                    result = loop.run_until_complete(health_task.execute())
                    if result:
                        self.logger.info("健康检查任务完成")
                    else:
                        self.logger.warning("健康检查未通过")
            except RuntimeError:
                # 如果没有事件循环，创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(health_task.execute())
                    if result:
                        self.logger.info("健康检查任务完成")
                    else:
                        self.logger.warning("健康检查未通过")
                finally:
                    loop.close()
            
        except Exception as error:
            self.logger.error(f"健康检查任务执行失败: {error}", exc_info=True)

    def _generate_status_report(self) -> str:
        """
        生成状态报告内容
        
        Returns:
            格式化的报告文本
        """
        # 获取关键统计数据
        subscriptions = self.database_manager.get_all_subscriptions()
        
        report_lines = [
            "📊 Telegram Bot 状态报告",
            "=" * 30,
            f"活跃订阅数: {len(subscriptions)}",
            f"最近推送时间: {self._get_last_push_time()}",
            f"调度器状态: {'运行中' if self.scheduler.running else '已停止'}",
            "=" * 30
        ]
        
        return "\n".join(report_lines)

    def _get_last_push_time(self) -> str:
        """获取最近推送时间"""
        # TODO: 从数据库或日志中获取实际时间
        return "待实现"

    def set_bot(self, bot: "TelegramBot"):
        """
        设置Telegram Bot实例
        
        Args:
            bot: Telegram Bot实例
        """
        self.bot = bot
        self.logger.info("✅ Bot实例已设置到调度器")

    def start(self) -> None:
        """启动调度器"""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                self.logger.info("✅ 调度器启动成功")
            else:
                self.logger.warning("⚠️ 调度器已经在运行中")
        except Exception as error:
            self.logger.error(f"❌ 调度器启动失败: {error}")

    def stop(self) -> None:
        """停止调度器"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                self.logger.info("✅ 调度器已停止")
        except Exception as error:
            self.logger.error(f"❌ 调度器停止失败: {error}")

    def shutdown(self) -> None:
        """关闭调度器（兼容性方法）"""
        self.stop()