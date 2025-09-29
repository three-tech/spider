"""
SMS模块配置管理 - 统一配置访问接口
"""

from base.config import config
from typing import Dict, Any

# SMS模块配置访问对象
sms_config = config.get('sms', {})

def get_feishu_config() -> Dict[str, Any]:
    """
    获取飞书机器人配置
    
    Returns:
        飞书配置字典
    """
    return config.get('sms.feishu', {})

def is_feishu_enabled() -> bool:
    """检查飞书通知是否启用"""
    feishu_config = get_feishu_config()
    return feishu_config.get('enabled', False) and bool(feishu_config.get('webhook_url'))