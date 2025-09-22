"""
SMS模块配置管理
"""

import os
import json
from typing import Dict, Any, Optional

class SMSConfig:
    """SMS配置管理类"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径
        """
        if config_path is None:
            # 默认使用项目根目录的config.json
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(project_root, 'config.json')
        
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return {}
    
    def get_feishu_config(self) -> Dict[str, str]:
        """
        获取飞书机器人配置
        
        Returns:
            飞书配置字典
        """
        sms_config = self.config.get('sms', {})
        feishu_config = sms_config.get('feishu', {})
        
        return {
            'webhook_url': feishu_config.get('webhook_url', ''),
            'secret': feishu_config.get('secret', ''),
            'enabled': feishu_config.get('enabled', False)
        }
    
    def is_feishu_enabled(self) -> bool:
        """检查飞书通知是否启用"""
        feishu_config = self.get_feishu_config()
        return feishu_config.get('enabled', False) and bool(feishu_config.get('webhook_url'))

def get_sms_config(config_path: Optional[str] = None) -> SMSConfig:
    """
    获取SMS配置实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        SMS配置实例
    """
    return SMSConfig(config_path)