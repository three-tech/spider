"""
Telegram机器人工具函数

包含通用的工具函数和辅助类
"""
import re
from typing import Optional, List
from ..base.logger import get_logger


logger = get_logger("telegram_utils")


def validate_telegram_chat_id(chat_id: str) -> bool:
    """
    验证Telegram聊天ID格式
    
    Args:
        chat_id: 聊天ID字符串
        
    Returns:
        是否为有效的聊天ID格式
    """
    if not chat_id:
        return False
    
    # Telegram聊天ID通常为数字，可能以负号开头（群组）
    return re.match(r"^-?\d+$", str(chat_id)) is not None


def format_message_content(content: str, max_length: int = 4096) -> List[str]:
    """
    格式化消息内容，处理长度限制
    
    Args:
        content: 原始内容
        max_length: 单条消息最大长度
        
    Returns:
        分割后的消息列表
    """
    if len(content) <= max_length:
        return [content]
    
    # 简单分割逻辑（可优化为按段落分割）
    messages = []
    current_message = ""
    
    for paragraph in content.split("\n\n"):
        if len(current_message) + len(paragraph) + 2 > max_length:
            if current_message:
                messages.append(current_message.strip())
                current_message = ""
            
            # 如果单个段落就超过限制，强制分割
            while len(paragraph) > max_length:
                messages.append(paragraph[:max_length])
                paragraph = paragraph[max_length:]
        
        if current_message:
            current_message += "\n\n" + paragraph
        else:
            current_message = paragraph
    
    if current_message:
        messages.append(current_message.strip())
    
    return messages


def sanitize_user_input(text: str) -> str:
    """
    清理用户输入，防止注入攻击
    
    Args:
        text: 用户输入的文本
        
    Returns:
        清理后的安全文本
    """
    if not text:
        return ""
    
    # 移除潜在的恶意字符
    sanitized = re.sub(r"[<>{}]", "", text)
    # 限制长度
    return sanitized[:1000]


class MessageBuilder:
    """消息构建器，用于创建格式化的消息内容"""
    
    def __init__(self):
        self.lines = []
    
    def add_header(self, text: str) -> "MessageBuilder":
        """添加标题"""
        self.lines.append(f"📌 {text}")
        return self
    
    def add_section(self, text: str) -> "MessageBuilder":
        """添加章节"""
        self.lines.append(f"📋 {text}")
        return self
    
    def add_info(self, text: str) -> "MessageBuilder":
        """添加信息"""
        self.lines.append(f"ℹ️ {text}")
        return self
    
    def add_warning(self, text: str) -> "MessageBuilder":
        """添加警告"""
        self.lines.append(f"⚠️ {text}")
        return self
    
    def add_success(self, text: str) -> "MessageBuilder":
        """添加成功信息"""
        self.lines.append(f"✅ {text}")
        return self
    
    def add_error(self, text: str) -> "MessageBuilder":
        """添加错误信息"""
        self.lines.append(f"❌ {text}")
        return self
    
    def add_line(self, text: str = "") -> "MessageBuilder":
        """添加普通行"""
        self.lines.append(text)
        return self
    
    def add_separator(self) -> "MessageBuilder":
        """添加分隔线"""
        self.lines.append("─" * 30)
        return self
    
    def build(self) -> str:
        """构建最终消息"""
        return "\n".join(self.lines)
    
    def clear(self) -> "MessageBuilder":
        """清空内容"""
        self.lines.clear()
        return self