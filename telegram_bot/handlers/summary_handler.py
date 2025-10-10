"""
Summary 指令处理器

负责处理 /summary 指令，生成系统状态报告
"""
from typing import Dict, Any, List
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from base.logger import get_logger
from telegram_bot.database import TelegramDatabaseManager

logger = get_logger("telegram_summary")


class SummaryHandler:
    """Summary 指令处理器"""
    
    def __init__(self, db_manager: TelegramDatabaseManager):
        """
        初始化处理器
        
        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager
        self.handler = CommandHandler("summary", self.handle_summary)

    async def handle_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        处理 /summary 指令
        
        Args:
            update: Telegram 更新对象
            context: 上下文对象
        """
        try:
            # 检查用户权限
            user_id = update.effective_user.id
            admins = self.db_manager.get_admins()
            
            if user_id not in admins:
                await update.message.reply_text("❌ 权限不足：仅管理员可使用此指令")
                return
            
            # 生成报告
            report = await self.generate_summary_report()
            await update.message.reply_text(report, parse_mode='Markdown')
            
            logger.info(f"✅ 为管理员 {user_id} 生成系统报告")
            
        except Exception as error:
            logger.error(f"❌ 处理 /summary 指令失败: {error}")
            await update.message.reply_text("❌ 生成报告失败，请稍后重试")

    async def generate_summary_report(self) -> str:
        """
        生成系统状态报告
        
        Returns:
            格式化后的报告文本
        """
        try:
            # 获取系统统计数据
            stats = await self.get_system_stats()
            
            report = f"""
📊 **系统状态报告**

👥 **订阅统计**
- 活跃订阅数: {stats['active_subscriptions']}
- 总订阅数: {stats['total_subscriptions']}

📰 **内容统计**
- 总资源数: {stats['total_resources']}
- 今日新增资源: {stats['today_resources']}

🔄 **推送统计**
- 成功推送: {stats['successful_pushes']}
- 失败推送: {stats['failed_pushes']}
- 推送成功率: {stats['success_rate']:.1f}%

⚙️ **系统状态**
- 数据库连接: {'✅ 正常' if stats['db_status'] else '❌ 异常'}
- Bot 状态: {'✅ 正常' if stats['bot_status'] else '❌ 异常'}

⏰ **报告时间**: {stats['report_time']}
            """
            
            return report.strip()
            
        except Exception as error:
            logger.error(f"❌ 生成报告失败: {error}")
            return "❌ 生成报告失败，请检查系统状态"

    async def get_system_stats(self) -> Dict[str, Any]:
        """
        获取系统统计数据
        
        Returns:
            系统统计字典
        """
        try:
            # 获取订阅统计
            all_subscriptions = self.db_manager.get_all_subscriptions()
            active_subscriptions = self.db_manager.get_active_subscriptions()
            
            # 获取资源统计（需要实现相关方法）
            total_resources = await self.get_total_resources_count()
            today_resources = await self.get_today_resources_count()
            
            # 获取推送统计（需要从任务执行结果中获取）
            push_stats = await self.get_push_statistics()
            
            # 检查系统状态
            db_status = await self.check_database_status()
            bot_status = await self.check_bot_status()
            
            # 计算成功率
            total_pushes = push_stats['successful_pushes'] + push_stats['failed_pushes']
            success_rate = (push_stats['successful_pushes'] / total_pushes * 100) if total_pushes > 0 else 0
            
            from datetime import datetime
            return {
                'active_subscriptions': len(active_subscriptions),
                'total_subscriptions': len(all_subscriptions),
                'total_resources': total_resources,
                'today_resources': today_resources,
                'successful_pushes': push_stats['successful_pushes'],
                'failed_pushes': push_stats['failed_pushes'],
                'success_rate': success_rate,
                'db_status': db_status,
                'bot_status': bot_status,
                'report_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as error:
            logger.error(f"❌ 获取系统统计失败: {error}")
            # 返回默认值
            return {
                'active_subscriptions': 0,
                'total_subscriptions': 0,
                'total_resources': 0,
                'today_resources': 0,
                'successful_pushes': 0,
                'failed_pushes': 0,
                'success_rate': 0,
                'db_status': False,
                'bot_status': False,
                'report_time': '未知'
            }

    async def get_total_resources_count(self) -> int:
        """
        获取总资源数
        
        Returns:
            资源总数
        """
        try:
            # 查询ResourceX表总数
            session = self.db_manager.Session()
            try:
                result = session.execute("SELECT COUNT(*) FROM resource.resource_x").fetchone()
                return result[0] if result else 0
            finally:
                session.close()
        except Exception as error:
            logger.error(f"❌ 获取资源总数失败: {error}")
            return 0

    async def get_today_resources_count(self) -> int:
        """
        获取今日新增资源数
        
        Returns:
            今日新增资源数
        """
        try:
            from datetime import datetime, date
            session = self.db_manager.Session()
            try:
                today = date.today()
                result = session.execute(
                    "SELECT COUNT(*) FROM resource.resource_x WHERE DATE(publishTime) = :today",
                    {'today': today}
                ).fetchone()
                return result[0] if result else 0
            finally:
                session.close()
        except Exception as error:
            logger.error(f"❌ 获取今日资源数失败: {error}")
            return 0

    async def get_push_statistics(self) -> Dict[str, int]:
        """
        获取推送统计信息
        
        Returns:
            推送统计字典
        """
        # 这里需要从任务执行结果中获取，暂时返回默认值
        # 在实际实现中，应该从数据库或内存中获取最新的推送统计
        return {
            'successful_pushes': 0,
            'failed_pushes': 0
        }

    async def check_database_status(self) -> bool:
        """
        检查数据库状态
        
        Returns:
            数据库是否正常
        """
        try:
            session = self.db_manager.Session()
            session.execute("SELECT 1")
            session.close()
            return True
        except Exception:
            return False

    async def check_bot_status(self) -> bool:
        """
        检查Bot状态
        
        Returns:
            Bot是否正常
        """
        # 这里需要实际的Bot状态检查逻辑
        # 暂时返回True，实际实现中应该检查Bot API连接
        return True

    def get_handler(self) -> CommandHandler:
        """
        获取指令处理器
        
        Returns:
            CommandHandler 实例
        """
        return self.handler