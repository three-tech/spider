"""
Telegram机器人自定义异常

定义项目特定的异常类型，便于错误处理和调试
"""


class TelegramBotError(Exception):
    """Telegram机器人基础异常"""
    
    def __init__(self, message: str, error_code: str | None = None):
        """
        初始化异常
        
        Args:
            message: 错误消息
            error_code: 错误代码（可选）
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
    
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ConfigError(TelegramBotError):
    """配置相关异常"""
    
    def __init__(self, message: str):
        super().__init__(message, "CONFIG_ERROR")


class DatabaseError(TelegramBotError):
    """数据库操作异常"""
    
    def __init__(self, message: str, operation: str = None):
        super().__init__(message, "DATABASE_ERROR")
        self.operation = operation


class AuthenticationError(TelegramBotError):
    """认证相关异常"""
    
    def __init__(self, message: str):
        super().__init__(message, "AUTH_ERROR")


class SchedulerError(TelegramBotError):
    """调度器相关异常"""
    
    def __init__(self, message: str):
        super().__init__(message, "SCHEDULER_ERROR")


class MessageFormatError(TelegramBotError):
    """消息格式异常"""
    
    def __init__(self, message: str):
        super().__init__(message, "MESSAGE_FORMAT_ERROR")


class SubscriptionError(TelegramBotError):
    """订阅管理异常"""
    
    def __init__(self, message: str, chat_id: int | None = None, tag: str | None = None):
        super().__init__(message, "SUBSCRIPTION_ERROR")
        self.chat_id = chat_id
        self.tag = tag


class ContentPushError(TelegramBotError):
    """内容推送异常"""
    
    def __init__(self, message: str, chat_id: int | None = None):
        super().__init__(message, "CONTENT_PUSH_ERROR")
        self.chat_id = chat_id