"""
自动报告处理器

负责在任务完成后自动生成并发送报告
"""
import sys
import os
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from base.logger import get_logger
from telegram_bot.handlers.summary_handler import SummaryHandler
from telegram_bot.handlers.alert_handler import AlertHandler

logger = get_logger("telegram_report")


class ReportHandler:
    """自动报告处理器"""
    
    def __init__(self, summary_handler: SummaryHandler, alert_handler: AlertHandler):
        """
        初始化报告处理器
        
        Args:
            summary_handler: Summary处理器实例
            alert_handler: 警报处理器实例
        """
        self.summary_handler = summary_handler
        self.alert_handler = alert_handler

    async def send_task_report(self, task_stats: Dict[str, Any], task_type: str = "push") -> bool:
        """
        发送任务完成报告
        
        Args:
            task_stats: 任务统计信息
            task_type: 任务类型（push/health_check）
            
        Returns:
            发送是否成功
        """
        try:
            # 生成报告消息
            report_message = await self.generate_task_report(task_stats, task_type)
            
            # 获取所有管理员
            admins = self.summary_handler.db_manager.get_admins()
            if not admins:
                logger.warning("⚠️ 未找到管理员，跳过报告发送")
                return False
            
            # 发送给所有管理员
            success_count = 0
            for admin_id in admins:
                try:
                    sent = await self.summary_handler.bot_instance.send_message(
                        chat_id=admin_id,
                        text=report_message,
                        parse_mode='Markdown'
                    )
                    if sent:
                        success_count += 1
                        logger.info(f"✅ 报告发送成功给管理员 {admin_id}")
                    else:
                        logger.warning(f"⚠️ 报告发送失败给管理员 {admin_id}")
                except Exception as admin_error:
                    logger.error(f"❌ 发送报告给管理员 {admin_id} 失败: {admin_error}")
            
            logger.info(f"📊 任务报告发送完成: {success_count}/{len(admins)} 个管理员")
            return success_count > 0
            
        except Exception as error:
            logger.error(f"❌ 发送任务报告失败: {error}")
            return False

    async def generate_task_report(self, task_stats: Dict[str, Any], task_type: str) -> str:
        """
        生成任务报告
        
        Args:
            task_stats: 任务统计信息
            task_type: 任务类型
            
        Returns:
            格式化后的报告文本
        """
        from datetime import datetime
        
        if task_type == "push":
            return await self.generate_push_task_report(task_stats)
        elif task_type == "health_check":
            return await self.generate_health_check_report(task_stats)
        else:
            return await self.generate_generic_task_report(task_stats, task_type)

    async def generate_push_task_report(self, task_stats: Dict[str, Any]) -> str:
        """
        生成推送任务报告
        
        Args:
            task_stats: 推送任务统计信息
            
        Returns:
            推送任务报告文本
        """
        total_pushes = task_stats.get('successful_pushes', 0) + task_stats.get('failed_pushes', 0)
        success_rate = (task_stats.get('successful_pushes', 0) / total_pushes * 100) if total_pushes > 0 else 0
        
        # 判断任务状态
        if task_stats.get('failed_pushes', 0) > 0:
            status_icon = "⚠️"
            status_text = "部分成功"
        elif total_pushes == 0:
            status_icon = "ℹ️"
            status_text = "无新内容"
        else:
            status_icon = "✅"
            status_text = "完全成功"
        
        report = f"""
{status_icon} **推送任务完成报告**

📊 **任务统计**
- 状态: {status_text}
- 活跃订阅数: {task_stats.get('total_subscriptions', 0)}
- 已处理订阅: {task_stats.get('processed_subscriptions', 0)}
- 发现新资源: {task_stats.get('new_resources_found', 0)}
- 成功推送: {task_stats.get('successful_pushes', 0)}
- 失败推送: {task_stats.get('failed_pushes', 0)}
- 推送成功率: {success_rate:.1f}%

⏰ **完成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 **说明**: 此报告为自动生成，如需详细统计请使用 /summary 指令
        """
        
        return report.strip()

    async def generate_health_check_report(self, task_stats: Dict[str, Any]) -> str:
        """
        生成健康检查报告
        
        Args:
            task_stats: 健康检查统计信息
            
        Returns:
            健康检查报告文本
        """
        status_icon = "✅" if task_stats.get('health_status', False) else "❌"
        status_text = "正常" if task_stats.get('health_status', False) else "异常"
        
        report = f"""
{status_icon} **系统健康检查报告**

🏥 **检查结果**
- 状态: {status_text}
- 数据库连接: {'✅ 正常' if task_stats.get('db_status', False) else '❌ 异常'}
- Bot 连接: {'✅ 正常' if task_stats.get('bot_status', False) else '❌ 异常'}
- 活跃订阅数: {task_stats.get('active_subscriptions', 0)}

⏰ **检查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 **说明**: 此报告为自动生成，如需详细统计请使用 /summary 指令
        """
        
        return report.strip()

    async def generate_generic_task_report(self, task_stats: Dict[str, Any], task_type: str) -> str:
        """
        生成通用任务报告
        
        Args:
            task_stats: 任务统计信息
            task_type: 任务类型
            
        Returns:
            通用任务报告文本
        """
        from datetime import datetime
        
        report = f"""
📋 **{task_type.upper()} 任务完成报告**

📊 **任务统计**
{chr(10).join([f"- {key}: {value}" for key, value in task_stats.items()])}

⏰ **完成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return report.strip()

    async def send_daily_summary(self) -> bool:
        """
        发送每日汇总报告
        
        Returns:
            发送是否成功
        """
        try:
            # 生成系统状态报告
            system_report = await self.summary_handler.generate_summary_report()
            
            # 获取所有管理员
            admins = self.summary_handler.db_manager.get_admins()
            if not admins:
                logger.warning("⚠️ 未找到管理员，跳过每日报告发送")
                return False
            
            # 添加每日报告标题
            from datetime import datetime
            daily_report = f"""
📅 **每日系统报告 - {datetime.now().strftime('%Y-%m-%d')}**

{system_report}
            """
            
            # 发送给所有管理员
            success_count = 0
            for admin_id in admins:
                try:
                    sent = await self.summary_handler.bot_instance.send_message(
                        chat_id=admin_id,
                        text=daily_report.strip(),
                        parse_mode='Markdown'
                    )
                    if sent:
                        success_count += 1
                        logger.info(f"✅ 每日报告发送成功给管理员 {admin_id}")
                    else:
                        logger.warning(f"⚠️ 每日报告发送失败给管理员 {admin_id}")
                except Exception as admin_error:
                    logger.error(f"❌ 发送每日报告给管理员 {admin_id} 失败: {admin_error}")
            
            logger.info(f"📅 每日报告发送完成: {success_count}/{len(admins)} 个管理员")
            return success_count > 0
            
        except Exception as error:
            logger.error(f"❌ 发送每日报告失败: {error}")
            return False