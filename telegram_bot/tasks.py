"""
Telegram Bot 任务模块

负责实现具体的推送任务逻辑
"""
from typing import List, Dict, Any, Optional
from ..base.logger import get_logger

from typing import TYPE_CHECKING, TYPE_CHECKING
from ..base.logger import get_logger

# 类型检查导入，避免循环依赖
if TYPE_CHECKING:
    from telegram_bot.database import TelegramDatabaseManager, TelegramSubscriptions
    from telegram_bot.bot import TelegramBot
else:
    # 运行时占位符
    TelegramDatabaseManager = object
    TelegramSubscriptions = object
    TelegramBot = object

logger = get_logger("telegram_tasks")


class PushTask:
    """推送任务类"""
    
    def __init__(self, db_manager: "TelegramDatabaseManager", bot: "TelegramBot"):
        """
        初始化推送任务
        
        Args:
            db_manager: 数据库管理器
            bot: Telegram Bot实例
        """
        self.db_manager = db_manager
        self.bot = bot
        self.stats = {
            'total_subscriptions': 0,
            'processed_subscriptions': 0,
            'new_resources_found': 0,
            'successful_pushes': 0,
            'failed_pushes': 0
        }

    def format_message(self, resource: Dict[str, Any]) -> str:
        """
        格式化推送消息
        
        Args:
            resource: 资源数据
            
        Returns:
            格式化后的消息文本
        """
        try:
            # 基础信息
            message_parts = []
            
            # 标题
            if resource.get('title'):
                message_parts.append(f"📰 **{resource['title']}**")
            elif resource.get('content'):
                # 如果没有标题，使用内容的前50个字符作为标题
                content_preview = resource['content'][:50].strip()
                if len(resource['content']) > 50:
                    content_preview += "..."
                message_parts.append(f"📰 **{content_preview}**")
            
            # 内容
            if resource.get('content'):
                # 限制内容长度，避免消息过长
                content = resource['content']
                if len(content) > 500:
                    content = content[:500] + "..."
                message_parts.append(f"\n{content}")
            
            # 标签
            if resource.get('tags'):
                tags = resource['tags']
                if isinstance(tags, str):
                    message_parts.append(f"\n🏷️ 标签: {tags}")
            
            # 发布时间
            if resource.get('publish_time'):
                message_parts.append(f"\n⏰ 发布时间: {resource['publish_time']}")
            
            # 资源ID
            message_parts.append(f"\n🆔 资源ID: {resource['id']}")
            
            # 链接（如果有）
            if resource.get('url'):
                message_parts.append(f"\n🔗 原文链接: {resource['url']}")
            
            return "\n".join(message_parts)
            
        except Exception as error:
            logger.error(f"❌ 格式化消息失败: {error}")
            return f"📰 新内容推送 (资源ID: {resource.get('id', '未知')})"

    async def push_to_subscription(self, subscription: TelegramSubscriptions) -> bool:
        """
        向单个订阅推送新内容
        
        Args:
            subscription: 订阅对象
            
        Returns:
            推送是否成功
        """
        try:
            logger.info(f"📤 开始处理订阅: chat_id={subscription.chat_id}, tag='{subscription.tag}'")
            
            # 获取新资源
            new_resources = self.db_manager.get_new_resources_for_subscription(subscription)
            
            if not new_resources:
                logger.info(f"📭 没有新资源需要推送: chat_id={subscription.chat_id}")
                return True
            
            success_count = 0
            total_count = len(new_resources)
            
            # 按资源ID排序推送（从小到大）
            new_resources.sort(key=lambda x: x['id'])
            
            for resource in new_resources:
                try:
                    # 格式化消息
                    message = self.format_message(resource)
                    
                    # 发送消息
                    sent = await self.bot.send_message(
                        chat_id=subscription.chat_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    
                    if sent:
                        success_count += 1
                        logger.info(f"✅ 推送成功: chat_id={subscription.chat_id}, resource_id={resource['id']}")
                        
                        # 更新订阅进度
                        self.db_manager.update_subscription_progress(
                            chat_id=subscription.chat_id,
                            tag=subscription.tag,
                            last_resource_x_id=resource['id']
                        )
                    else:
                        logger.error(f"❌ 推送失败: chat_id={subscription.chat_id}, resource_id={resource['id']}")
                        # 如果推送失败，停止当前订阅的处理
                        break
                        
                except Exception as resource_error:
                    logger.error(f"❌ 处理资源失败: {resource_error}")
                    # 继续处理下一个资源
                    continue
            
            # 更新统计信息
            self.stats['new_resources_found'] += total_count
            self.stats['successful_pushes'] += success_count
            self.stats['failed_pushes'] += (total_count - success_count)
            
            if success_count > 0:
                logger.info(f"✅ 订阅处理完成: chat_id={subscription.chat_id}, 成功推送 {success_count}/{total_count} 个资源")
                return True
            else:
                logger.warning(f"⚠️ 订阅处理失败: chat_id={subscription.chat_id}, 所有资源推送失败")
                return False
                
        except Exception as error:
            logger.error(f"❌ 处理订阅失败: {error}")
            self.stats['failed_pushes'] += len(new_resources) if 'new_resources' in locals() else 1
            return False

    async def execute(self) -> Dict[str, Any]:
        """
        执行推送任务
        
        Returns:
            任务执行结果统计
        """
        try:
            logger.info("🚀 开始执行推送任务...")
            
            # 重置统计信息
            self.stats = {
                'total_subscriptions': 0,
                'processed_subscriptions': 0,
                'new_resources_found': 0,
                'successful_pushes': 0,
                'failed_pushes': 0
            }
            
            # 获取所有活跃订阅
            subscriptions = self.db_manager.get_active_subscriptions()
            self.stats['total_subscriptions'] = len(subscriptions)
            
            if not subscriptions:
                logger.info("📭 没有活跃订阅，任务结束")
                return self.stats
            
            logger.info(f"📋 找到 {len(subscriptions)} 个活跃订阅")
            
            # 处理每个订阅
            for subscription in subscriptions:
                try:
                    self.stats['processed_subscriptions'] += 1
                    await self.push_to_subscription(subscription)
                    
                except Exception as sub_error:
                    logger.error(f"❌ 处理订阅异常: {sub_error}")
                    continue
            
            # 输出任务统计
            logger.info(f"📊 推送任务完成统计:")
            logger.info(f"   - 总订阅数: {self.stats['total_subscriptions']}")
            logger.info(f"   - 已处理订阅: {self.stats['processed_subscriptions']}")
            logger.info(f"   - 发现新资源: {self.stats['new_resources_found']}")
            logger.info(f"   - 成功推送: {self.stats['successful_pushes']}")
            logger.info(f"   - 失败推送: {self.stats['failed_pushes']}")
            
            return self.stats
            
        except Exception as error:
            logger.error(f"❌ 推送任务执行失败: {error}")
            return self.stats


class HealthCheckTask:
    """健康检查任务"""
    
    def __init__(self, db_manager: "TelegramDatabaseManager", bot: "TelegramBot"):
        """
        初始化健康检查任务
        
        Args:
            db_manager: 数据库管理器
            bot: Telegram Bot实例
        """
        self.db_manager = db_manager
        self.bot = bot

    async def execute(self) -> bool:
        """
        执行健康检查
        
        Returns:
            检查是否通过
        """
        try:
            logger.info("🔍 开始健康检查...")
            
            # 检查数据库连接
            try:
                subscriptions = self.db_manager.get_active_subscriptions()
                db_status = f"✅ 数据库连接正常 (活跃订阅: {len(subscriptions)})"
            except Exception as db_error:
                db_status = f"❌ 数据库连接异常: {db_error}"
            
            # 检查Bot连接
            try:
                bot_info = await self.bot.get_me()
                bot_status = f"✅ Bot连接正常 (@{bot_info.username})"
            except Exception as bot_error:
                bot_status = f"❌ Bot连接异常: {bot_error}"
            
            # 汇总检查结果
            health_status = f"""
🏥 健康检查报告:
{db_status}
{bot_status}
            """
            
            logger.info(health_status)
            
            # 发送到警报频道（如果有）
            alert_channel_id = self.db_manager.get_alert_channel_id()
            if alert_channel_id:
                try:
                    await self.bot.send_message(
                        chat_id=alert_channel_id,
                        text=health_status,
                        parse_mode='Markdown'
                    )
                except Exception as alert_error:
                    logger.error(f"❌ 发送健康检查报告失败: {alert_error}")
            
            return "❌" not in db_status and "❌" not in bot_status
            
        except Exception as error:
            logger.error(f"❌ 健康检查执行失败: {error}")
            return False