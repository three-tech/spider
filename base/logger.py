"""
统一日志管理模块 - 提供高级日志功能和结构化日志支持
"""

import logging
import os
import sys
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Union
from pathlib import Path
from functools import wraps

# 尝试导入loguru，如果可用则使用更高级的日志功能
try:
    from loguru import logger as loguru_logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False

from .config import config


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self._extra_fields: Dict[str, Any] = {}
    
    def with_fields(self, **fields) -> 'StructuredLogger':
        """添加上下文字段"""
        new_logger = StructuredLogger(self.name)
        new_logger._extra_fields = {**self._extra_fields, **fields}
        return new_logger
    
    def _format_message(self, message: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """格式化结构化日志消息"""
        all_fields = {**self._extra_fields, **(extra or {})}
        
        if LOGURU_AVAILABLE and config.get_logging_config().get('structured', {}).get('enabled', True):
            # 使用loguru的结构化日志
            return f"{message} | {json.dumps(all_fields, ensure_ascii=False)}"
        else:
            # 标准logging的结构化日志
            if all_fields:
                return f"{message} - {json.dumps(all_fields, ensure_ascii=False)}"
            return message
    
    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        formatted_message = self._format_message(message, kwargs)
        self.logger.debug(formatted_message)
    
    def info(self, message: str, **kwargs):
        """记录信息日志"""
        formatted_message = self._format_message(message, kwargs)
        self.logger.info(formatted_message)
    
    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        formatted_message = self._format_message(message, kwargs)
        self.logger.warning(formatted_message)
    
    def error(self, message: str, **kwargs):
        """记录错误日志"""
        formatted_message = self._format_message(message, kwargs)
        self.logger.error(formatted_message)
    
    def exception(self, message: str, **kwargs):
        """记录异常日志"""
        formatted_message = self._format_message(message, kwargs)
        self.logger.exception(formatted_message)
    
    def critical(self, message: str, **kwargs):
        """记录严重错误日志"""
        formatted_message = self._format_message(message, kwargs)
        self.logger.critical(formatted_message)


class LoggerManager:
    """统一日志管理器"""
    
    _loggers: Dict[str, StructuredLogger] = {}
    _initialized = False
    
    @classmethod
    def initialize(cls) -> None:
        """初始化日志系统"""
        if cls._initialized:
            return
        
        log_config = config.get_logging_config()
        advanced_config = log_config.get('advanced', {})
        handlers_config = log_config.get('handlers', {})
        levels_config = log_config.get('levels', {})
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 控制台处理器
        if handlers_config.get('console_enabled', True):
            console_level = getattr(logging, handlers_config.get('console_level', 'INFO').upper())
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(console_level)
            console_handler.setFormatter(cls._create_formatter())
            root_logger.addHandler(console_handler)
        
        # 文件处理器
        if handlers_config.get('file_enabled', True):
            file_level = getattr(logging, handlers_config.get('file_level', 'DEBUG').upper())
            file_path = log_config.get('file_path', 'logs/spider.log')
            
            # 确保使用项目根目录的绝对路径
            if not os.path.isabs(file_path):
                project_root = Path(__file__).parent.parent
                file_path = project_root / file_path
            
            # 确保日志目录存在
            log_dir = Path(file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(file_path, encoding='utf-8')
            file_handler.setLevel(file_level)
            file_handler.setFormatter(cls._create_formatter())
            root_logger.addHandler(file_handler)
        
        # 配置模块特定日志级别
        for module_name, level_name in levels_config.items():
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(getattr(logging, level_name.upper()))
        
        cls._initialized = True
    
    @classmethod
    def _create_formatter(cls) -> logging.Formatter:
        """创建日志格式化器"""
        log_config = config.get_logging_config()
        format_str = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        return logging.Formatter(format_str)
    
    @classmethod
    def get_logger(cls, name: str) -> StructuredLogger:
        """
        获取结构化日志记录器
        
        Args:
            name: 日志记录器名称（通常是模块名）
            
        Returns:
            结构化日志记录器实例
        """
        if not cls._initialized:
            cls.initialize()
        
        if name not in cls._loggers:
            cls._loggers[name] = StructuredLogger(name)
        
        return cls._loggers[name]
    
    @classmethod
    def get_module_logger(cls, module: str) -> StructuredLogger:
        """获取模块日志记录器（便捷方法）"""
        return cls.get_logger(module)
    
    @classmethod
    def setup_loguru(cls) -> bool:
        """设置loguru日志系统（如果可用）"""
        if not LOGURU_AVAILABLE:
            return False
        
        log_config = config.get_logging_config()
        advanced_config = log_config.get('advanced', {})
        
        # 配置loguru
        loguru_logger.remove()
        
        # 控制台输出
        if log_config.get('handlers', {}).get('console_enabled', True):
            console_level = log_config.get('handlers', {}).get('console_level', 'INFO')
            loguru_logger.add(
                sys.stdout,
                level=console_level,
                format="{time:YYYY-MM-DD HH:mm:ss} - {name} - {level} - {message}",
                filter=lambda record: record["level"].no >= getattr(loguru_logger.level(console_level), "no", 20)
            )
        
        # 文件输出
        if log_config.get('handlers', {}).get('file_enabled', True):
            file_path = log_config.get('file_path', 'logs/spider.log')
            file_level = log_config.get('handlers', {}).get('file_level', 'DEBUG')
            
            # 确保使用项目根目录的绝对路径
            if not os.path.isabs(file_path):
                project_root = Path(__file__).parent.parent
                file_path = project_root / file_path
            
            loguru_logger.add(
                file_path,
                level=file_level,
                format="{time:YYYY-MM-DD HH:mm:ss} - {name} - {level} - {message}",
                rotation=advanced_config.get('rotation'),
                retention=advanced_config.get('retention'),
                compression=advanced_config.get('compression'),
                encoding='utf-8'
            )
        
        return True


# 装饰器函数
def log_function_call(level: str = "INFO"):
    """记录函数调用的装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = LoggerManager.get_logger(func.__module__)
            start_time = time.time()
            
            # 记录函数开始
            logger.info(f"调用函数: {func.__name__}", function=func.__name__, args=len(args), kwargs=len(kwargs))
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 记录函数完成
                log_method = getattr(logger, level.lower())
                log_method(f"函数完成: {func.__name__}", 
                          function=func.__name__, 
                          execution_time=execution_time,
                          result_type=type(result).__name__)
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"函数异常: {func.__name__}", 
                           function=func.__name__, 
                           execution_time=execution_time,
                           error=str(e),
                           error_type=type(e).__name__)
                raise
        
        return wrapper
    return decorator


class TimerContext:
    """计时上下文管理器"""
    
    def __init__(self, name: str, logger: Optional[StructuredLogger] = None):
        self.name = name
        self.logger = logger or LoggerManager.get_logger("timer")
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"开始计时: {self.name}", timer_name=self.name, action="start")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            execution_time = time.time() - self.start_time
            if exc_type is None:
                self.logger.info(f"计时完成: {self.name}", 
                               timer_name=self.name, 
                               execution_time=execution_time,
                               action="complete")
            else:
                self.logger.error(f"计时异常: {self.name}", 
                                 timer_name=self.name, 
                                 execution_time=execution_time,
                                 error=str(exc_val),
                                 action="error")


# 便捷函数（保持向后兼容）
def get_logger(name: str) -> StructuredLogger:
    """获取日志记录器的便捷函数（向后兼容）"""
    return LoggerManager.get_logger(name)


def setup_logging() -> None:
    """设置日志系统（便捷函数）"""
    LoggerManager.initialize()
    if LOGURU_AVAILABLE:
        LoggerManager.setup_loguru()


# 自动初始化
setup_logging()