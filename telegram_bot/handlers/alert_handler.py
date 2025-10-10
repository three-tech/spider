"""
异常报警处理器

负责在系统异常时发送警报通知
"""
import sys
import os
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from base.logger import get_logger
from telegram_bot.database import TelegramDatabaseManager

logger = get_logger("telegram_alert")


class AlertHandler:
    """异常报警处理器"""
    
    def __init__(self, db_manager: TelegramDatabaseManager, bot_instance=None):
        """
        初始化报警处理器
        
        Args:
            db_manager: 数据库管理器
            bot_instance: Bot实例（可选）
        """
        self.db_manager = db_manager
        self.bot_instance = bot_instance

    async def send_alert(self, alert_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        发送警报通知
        
        Args:
            alert_type: 警报类型
            message: 警报消息
            details: 详细信息（可选）
            
        Returns:
            发送是否成功
        """
        try:
            # 获取警报频道ID
            alert_channel_id = self.db_manager.get_alert_channel_id()
            if not alert_channel_id:
                logger.warning("⚠️ 未配置警报频道，跳过警报发送")
                return False
            
            if not self.bot_instance:
                logger.warning("⚠️ Bot实例未设置，无法发送警报")
                return False
            
            # 格式化警报消息
            alert_message = self.format_alert_message(alert_type, message, details)
            
            # 发送警报
            sent = await self.bot_instance.send_message(
                chat_id=alert_channel_id,
                text=alert_message,
                parse_mode='Markdown'
            )
            
            if sent:
                logger.info(f"✅ 警报发送成功: {alert_type}")
                return True
            else:
                logger.error(f"❌ 警报发送失败: {alert_type}")
                return False
                
        except Exception as error:
            logger.error(f"❌ 发送警报异常: {error}")
            return False

    def format_alert_message(self, alert_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> str:
        """
        格式化警报消息
        
        Args:
            alert_type: 警报类型
            message: 警报消息
            details: 详细信息
            
        Returns:
            格式化后的消息
        """
        from datetime import datetime
        
        alert_icons = {
            'error': '🚨',
            'warning': '⚠️',
            'info': 'ℹ️',
            'success': '✅'
        }
        
        icon = alert_icons.get(alert_type, '📢')
        
        alert_message = f"""
{icon} **系统警报 - {alert_type.upper()}**

📝 **消息**: {message}

⏰ **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        # 添加详细信息
        if details:
            details_text = "\n".join([f"- {key}: {value}" for key, value in details.items()])
            alert_message += f"\n\n📋 **详细信息**:\n{details_text}"
        
        return alert_message.strip()

    async def send_database_alert(self, operation: str, error: Exception) -> bool:
        """
        发送数据库操作警报
        
        Args:
            operation: 数据库操作描述
            error: 异常对象
            
        Returns:
            发送是否成功
        """
        details = {
            '操作': operation,
            '异常类型': type(error).__name__,
            '异常信息': str(error)
        }
        
        return await self.send_alert(
            alert_type='error',
            message=f"数据库操作失败: {operation}",
            details=details
        )

    async def send_api_alert(self, api_name: str, error: Exception, chat_id: Optional[int] = None) -> bool:
        """
        发送API调用警报
        
        Args:
            api_name: API名称
            error: 异常对象
            chat_id: 相关聊天ID（可选）
            
        Returns:
            发送是否成功
        """
        details = {
            'API名称': api_name,
            '异常类型': type(error).__name__,
            '异常信息': str(error)
        }
        
        if chat_id:
            details['聊天ID'] = str(chat_id)
        
        return await self.send_alert(
            alert_type='error',
            message=f"API调用失败: {api_name}",
            details=details
        )

    async def send_push_task_alert(self, task_stats: Dict[str, Any], error: Optional[Exception] = None) -> bool:
        """
        发送推送任务警报
        
        Args:
            task_stats: 任务统计信息
            error: 异常对象（可选）
            
        Returns:
            发送是否成功
        """
        if error:
            # 任务执行失败
            details = {
                '总订阅数': task_stats.get('total_subscriptions', 0),
                '已处理订阅': task_stats.get('processed_subscriptions', 0),
                '异常类型': type(error).__name__,
                '异常信息': str(error)
            }
            
            return await self.send_alert(
                alert_type='error',
                message="推送任务执行失败",
                details=details
            )
        else:
            # 任务完成报告
            success_rate = 0
            total_pushes = task_stats.get('successful_pushes', 0) + task_stats.get('failed_pushes', 0)
            if total_pushes > 0:
                success_rate = (task_stats.get('successful_pushes', 0) / total_pushes) * 100
            
            details = {
                '总订阅数': task_stats.get('total_subscriptions', 0),
                '已处理订阅': task_stats.get('processed_subscriptions', 0),
                '发现新资源': task_stats.get('new_resources_found', 0),
                '成功推送': task_stats.get('successful_pushes', 0),
                '失败推送': task_stats.get('failed_pushes', 0),
                '推送成功率': f"{success_rate:.1f}%"
            }
            
            alert_type = 'warning' if success_rate < 80 else 'info'
            return await self.send_alert(
                alert_type=alert_type,
                message="推送任务完成报告",
                details=details
            )

    def set_bot_instance(self, bot_instance):
        """
        设置Bot实例
        
        Args:
            bot_instance: Bot实例
        """
        self.bot_instance = bot_instance