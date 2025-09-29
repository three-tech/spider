"""
Base module initialization
Import common utilities and loggers
"""
from base.logger import get_logger

# 提供向后兼容的logger实例
global_logger = get_logger('global')
database_logger = get_logger('database') 
spider_logger = get_logger('spider')
x_logger = get_logger('x')

__all__ = ['global_logger', 'database_logger', 'spider_logger', 'x_logger', 'get_logger']