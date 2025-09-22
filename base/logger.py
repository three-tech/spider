"""
日志管理模块
"""

import logging
import os
from typing import Optional
from .config import config

class LoggerManager:
    """日志管理器"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str, log_file: Optional[str] = None) -> logging.Logger:
        """
        获取日志记录器
        
        Args:
            name: 日志记录器名称
            log_file: 日志文件路径，如果不指定则使用配置中的默认路径
            
        Returns:
            日志记录器实例
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        
        # 避免重复添加处理器
        if logger.handlers:
            cls._loggers[name] = logger
            return logger
        
        # 获取日志配置
        log_config = config.get_logging_config()
        level = getattr(logging, log_config.get('level', 'INFO').upper())
        format_str = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        logger.setLevel(level)
        
        # 创建格式化器
        formatter = logging.Formatter(format_str)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 文件处理器
        if log_file is None:
            log_file = log_config.get('file_path', 'logs/spider.log')
        
        if log_file:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def setup_root_logger(cls) -> None:
        """设置根日志记录器"""
        log_config = config.get_logging_config()
        level = getattr(logging, log_config.get('level', 'INFO').upper())
        format_str = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        logging.basicConfig(
            level=level,
            format=format_str,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(
                    log_config.get('file_path', 'logs/spider.log'),
                    encoding='utf-8'
                )
            ]
        )

# 便捷函数
def get_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """获取日志记录器的便捷函数"""
    return LoggerManager.get_logger(name, log_file)