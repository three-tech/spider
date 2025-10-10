"""
广告系统处理器

负责处理广告相关的功能，包括广告入库、策略管理和投放控制
"""
from typing import Dict, Any, List, Optional, TYPE_CHECKING

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


logger = get_logger("ad_handler")


class AdHandler:
    """广告系统处理器"""
    
    def __init__(self, bot: 'TelegramBot'):
        """
        初始化广告处理器
        
        Args:
            bot: Telegram Bot实例
        """
        self.bot = bot
        self.database = bot.database
    
    async def handle_forwarded_message(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE') -> bool:
        """
        处理转发消息，识别并入库广告
        
        Args:
            update: 更新对象
            context: 上下文对象
            
        Returns:
            是否成功识别为广告并入库
        """
        try:
            message = update.message
            
            # 检查是否为转发消息
            if not message.forward_from_chat:
                return False
            
            # 检查来源是否为广告群
            source_chat_id = message.forward_from_chat.id
            if not self._is_ad_channel(source_chat_id):
                return False
            
            # 提取广告内容
            ad_content = self._extract_ad_content(message)
            if not ad_content:
                return False
            
            # 保存广告到数据库
            ad_id = self._save_advertisement(ad_content, source_chat_id)
            if ad_id:
                logger.info(f"✅ 广告入库成功: ID={ad_id}, 来源={source_chat_id}")
                await update.message.reply_text("✅ 广告已成功入库")
                return True
            else:
                logger.error("❌ 广告入库失败")
                return False
                
        except Exception as e:
            logger.error(f"处理转发消息失败: {e}")
            return False
    
    def _is_ad_channel(self, chat_id: int) -> bool:
        """
        检查是否为广告群
        
        Args:
            chat_id: 群组ID
            
        Returns:
            是否为广告群
        """
        try:
            # 从配置中获取广告群列表
            ad_channels = self.bot.config.get('ad_channels', [])
            return chat_id in ad_channels
        except Exception as e:
            logger.error(f"检查广告群失败: {e}")
            return False
    
    def _extract_ad_content(self, message) -> Dict[str, Any]:
        """
        从消息中提取广告内容
        
        Args:
            message: 消息对象
            
        Returns:
            广告内容字典
        """
        try:
            content = {
                'text': message.text or message.caption or '',
                'media_type': None,
                'media_url': None,
                'forward_from': message.forward_from_chat.id if message.forward_from_chat else None,
                'forward_date': message.forward_date,
                'message_id': message.message_id
            }
            
            # 处理不同类型的媒体
            if message.photo:
                content['media_type'] = 'photo'
                content['media_url'] = message.photo[-1].file_id  # 最高质量图片
            elif message.video:
                content['media_type'] = 'video'
                content['media_url'] = message.video.file_id
            elif message.document:
                content['media_type'] = 'document'
                content['media_url'] = message.document.file_id
            
            return content
        except Exception as e:
            logger.error(f"提取广告内容失败: {e}")
            return {}
    
    def _save_advertisement(self, ad_content: Dict[str, Any], source_chat_id: int) -> Optional[int]:
        """
        保存广告到数据库
        
        Args:
            ad_content: 广告内容
            source_chat_id: 来源群组ID
            
        Returns:
            广告ID或None
        """
        try:
            from datetime import datetime
            
            ad_config = {
                'content': ad_content,
                'source_chat_id': source_chat_id,
                'created_at': datetime.now().isoformat(),
                'is_active': True
            }
            
            # 使用数据库方法保存
            result = self.database.save_telegram_setting('advertisement', ad_config)
            if result:
                return result.id
            return None
                
        except Exception as e:
            logger.error(f"保存广告失败: {e}")
            return None
    
    async def handle_config_ad_command(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE') -> None:
        """
        处理 /config_ad 命令
        
        Args:
            update: 更新对象
            context: 上下文对象
        """
        try:
            user_id = update.effective_user.id
            
            # 检查管理员权限
            if not self._is_admin(user_id):
                await update.message.reply_text("❌ 权限不足，仅管理员可配置广告策略")
                return
            
            # 解析命令参数
            args = context.args or []
            if len(args) < 1:
                await update.message.reply_text(
                    "📋 使用方法: /config_ad <策略>\n\n"
                    "可用策略:\n"
                    "• after:2 - 每2条内容后插入广告\n"
                    "• after:3 - 每3条内容后插入广告\n"
                    "• ratio:0.1 - 10%的内容中插入广告\n"
                )
                return
            
            strategy = args[0]
            if not self._validate_ad_strategy(strategy):
                await update.message.reply_text("❌ 无效的策略格式")
                return
            
            # 保存广告策略
            if self._save_ad_strategy(strategy):
                await update.message.reply_text(f"✅ 广告策略已更新: {strategy}")
                logger.info(f"广告策略更新: {strategy} by user {user_id}")
            else:
                await update.message.reply_text("❌ 保存策略失败")
                
        except Exception as e:
            logger.error(f"处理/config_ad命令失败: {e}")
            await update.message.reply_text("❌ 配置广告策略失败")
    
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
    
    def _validate_ad_strategy(self, strategy: str) -> bool:
        """
        验证广告策略格式
        
        Args:
            strategy: 策略字符串
            
        Returns:
            策略是否有效
        """
        try:
            if strategy.startswith('after:'):
                num = int(strategy.split(':')[1])
                return 1 <= num <= 10
            elif strategy.startswith('ratio:'):
                ratio = float(strategy.split(':')[1])
                return 0 < ratio <= 0.5  # 最大50%广告比例
            return False
        except:
            return False
    
    def _save_ad_strategy(self, strategy: str) -> bool:
        """
        保存广告策略到数据库
        
        Args:
            strategy: 策略字符串
            
        Returns:
            保存是否成功
        """
        try:
            strategy_config = {
                'strategy': strategy,
                'created_at': datetime.now().isoformat()
            }
            
            # 保存策略到数据库
            result = self.database.save_telegram_setting('ad_strategy', strategy_config)
            return result is not None
                
        except Exception as e:
            logger.error(f"保存广告策略失败: {e}")
            return False
    
    def get_ad_strategy(self) -> Optional[str]:
        """
        获取当前广告策略
        
        Returns:
            策略字符串或None
        """
        try:
            # 从配置中获取广告策略
            return self.bot.config.get('ad_strategy')
        except Exception as e:
            logger.error(f"获取广告策略失败: {e}")
            return None
    
    def get_active_advertisements(self) -> List[Dict[str, Any]]:
        """
        获取所有活跃的广告
        
        Returns:
            广告列表
        """
        try:
            # 从配置中获取广告列表
            ads = self.bot.config.get('advertisements', [])
            return [ad for ad in ads if ad.get('is_active', True)]
        except Exception as e:
            logger.error(f"获取活跃广告失败: {e}")
            return []