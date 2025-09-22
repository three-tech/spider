"""
通知管理器
统一管理各种通知方式
"""

import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sms.feishu_bot import FeishuBot
from sms.config import get_sms_config
from base.logger import get_logger

class NotificationManager:
    """通知管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化通知管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.logger = get_logger(__name__)
        self.sms_config = get_sms_config(config_path)
        self.feishu_bot = None
        
        # 初始化飞书机器人
        self._init_feishu_bot()
    
    def _init_feishu_bot(self):
        """初始化飞书机器人"""
        if self.sms_config.is_feishu_enabled():
            feishu_config = self.sms_config.get_feishu_config()
            self.feishu_bot = FeishuBot(
                webhook_url=feishu_config['webhook_url'],
                secret=feishu_config.get('secret')
            )
            self.logger.info("✅ 飞书机器人初始化成功")
        else:
            self.logger.info("ℹ️ 飞书通知未启用")
    
    def send_xhs_publish_notification(self,
                                    xhs_account: str,
                                    image_count: int,
                                    image_paths: List[str],
                                    tweet_publish_time: str,
                                    tweet_content: str,
                                    tweet_author: str) -> Dict[str, Any]:
        """
        发送小红书发布通知
        
        Args:
            xhs_account: 小红书账户
            image_count: 图片数量
            image_paths: 本地图片路径列表
            tweet_publish_time: 推文发布时间
            tweet_content: 推文内容
            tweet_author: 推文作者
            
        Returns:
            发送结果
        """
        results = {}
        
        # 发送飞书通知
        if self.feishu_bot:
            try:
                self.logger.info("📤 发送飞书通知...")
                result = self.feishu_bot.send_xhs_publish_notification(
                    xhs_account=xhs_account,
                    image_count=image_count,
                    image_paths=image_paths,
                    tweet_publish_time=tweet_publish_time,
                    tweet_content=tweet_content,
                    tweet_author=tweet_author
                )
                
                results['feishu'] = result
                
                if result['success']:
                    self.logger.info("✅ 飞书通知发送成功")
                else:
                    self.logger.error(f"❌ 飞书通知发送失败: {result['message']}")
                    
            except Exception as e:
                error_msg = f"飞书通知发送异常: {str(e)}"
                self.logger.error(f"❌ {error_msg}")
                results['feishu'] = {
                    'success': False,
                    'message': error_msg,
                    'data': None
                }
        else:
            results['feishu'] = {
                'success': False,
                'message': '飞书机器人未配置或未启用',
                'data': None
            }
        
        return results
    
    def send_simple_notification(self,
                               xhs_account: str,
                               image_count: int,
                               tweet_author: str,
                               tweet_publish_time: str) -> Dict[str, Any]:
        """
        发送简化通知
        
        Args:
            xhs_account: 小红书账户
            image_count: 图片数量
            tweet_author: 推文作者
            tweet_publish_time: 推文发布时间
            
        Returns:
            发送结果
        """
        results = {}
        
        # 发送飞书通知
        if self.feishu_bot:
            try:
                self.logger.info("📤 发送简化飞书通知...")
                result = self.feishu_bot.send_simple_xhs_notification(
                    xhs_account=xhs_account,
                    image_count=image_count,
                    tweet_author=tweet_author,
                    tweet_publish_time=tweet_publish_time
                )
                
                results['feishu'] = result
                
                if result['success']:
                    self.logger.info("✅ 飞书通知发送成功")
                else:
                    self.logger.error(f"❌ 飞书通知发送失败: {result['message']}")
                    
            except Exception as e:
                error_msg = f"飞书通知发送异常: {str(e)}"
                self.logger.error(f"❌ {error_msg}")
                results['feishu'] = {
                    'success': False,
                    'message': error_msg,
                    'data': None
                }
        
        return results
    
    def is_notification_enabled(self) -> bool:
        """检查是否有任何通知方式启用"""
        return self.sms_config.is_feishu_enabled()

# 全局通知管理器实例
_notification_manager = None

def get_notification_manager(config_path: Optional[str] = None) -> NotificationManager:
    """
    获取通知管理器实例（单例模式）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        通知管理器实例
    """
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager(config_path)
    return _notification_manager