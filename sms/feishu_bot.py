"""飞书机器人消息发送接口"""

import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import base64
import os

class FeishuBot:
    """
    飞书机器人消息发送类
    支持文本消息、富文本消息、图片消息等
    """
    
    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        """
        初始化飞书机器人
        
        Args:
            webhook_url: 飞书机器人webhook地址
            secret: 机器人密钥（可选）
        """
        self.webhook_url = webhook_url
        self.secret = secret
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json; charset=utf-8'
        })
    
    def _generate_sign(self, timestamp: int) -> Optional[str]:
        """
        生成签名（如果配置了密钥）
        
        Args:
            timestamp: 时间戳
            
        Returns:
            签名字符串
        """
        if not self.secret:
            return None
        
        import hmac
        import hashlib
        
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"), 
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return sign
    
    def send_text(self, text: str) -> Dict[str, Any]:
        """
        发送纯文本消息
        
        Args:
            text: 文本内容
            
        Returns:
            发送结果
        """
        payload = {
            "msg_type": "text",
            "content": json.dumps({
                "text": text
            })
        }
        
        # 添加签名（如果需要）
        if self.secret:
            timestamp = int(time.time())
            sign = self._generate_sign(timestamp)
            if sign:
                payload["timestamp"] = str(timestamp)
                payload["sign"] = sign
        
        return self._send_request(payload)
    
    def send_rich_text(self, title: str, content: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        发送富文本消息
        
        Args:
            title: 消息标题
            content: 富文本内容
            
        Returns:
            发送结果
        """
        payload = {
            "msg_type": "post",
            "content": json.dumps({
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": content
                    }
                }
            })
        }
        
        # 添加签名（如果需要）
        if self.secret:
            timestamp = int(time.time())
            sign = self._generate_sign(timestamp)
            if sign:
                payload["timestamp"] = str(timestamp)
                payload["sign"] = sign
        
        return self._send_request(payload)
    
    def send_card(self, card_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送卡片消息
        
        Args:
            card_content: 卡片内容
            
        Returns:
            发送结果
        """
        payload = {
            "msg_type": "interactive",
            "card": card_content
        }
        
        # 添加签名（如果需要）
        if self.secret:
            timestamp = int(time.time())
            sign = self._generate_sign(timestamp)
            payload["timestamp"] = str(timestamp)
            payload["sign"] = sign
        
        return self._send_request(payload)
    
    def upload_image(self, image_path: str) -> Optional[str]:
        """
        获取图片信息（webhook方式不支持直接上传图片）
        
        Args:
            image_path: 本地图片路径
            
        Returns:
            图片文件名和大小信息
        """
        if not os.path.exists(image_path):
            return None
            
        try:
            file_name = os.path.basename(image_path)
            file_size = os.path.getsize(image_path)
            file_size_kb = file_size / 1024
            
            return f"{file_name} ({file_size_kb:.1f}KB)"
            
        except Exception as e:
            print(f"获取图片信息失败: {e}")
            return None
    
    def _serialize_payload(self, payload: Dict) -> Dict:
        """
        序列化payload，确保所有数据都可以JSON序列化
        
        Args:
            payload: 原始载荷
            
        Returns:
            可序列化的载荷
        """
        def serialize_value(value):
            if isinstance(value, datetime):
                return value.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value, dict):
                return {k: serialize_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [serialize_value(item) for item in value]
            else:
                return value
        
        return serialize_value(payload)
    
    def _send_request(self, payload: Dict) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            payload: 请求载荷
            
        Returns:
            响应结果
        """
        try:
            # 序列化payload确保JSON兼容
            serialized_payload = self._serialize_payload(payload)
            
            response = self.session.post(
                self.webhook_url,
                json=serialized_payload,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('code') == 0:
                return {
                    'success': True,
                    'message': '消息发送成功',
                    'data': result
                }
            else:
                return {
                    'success': False,
                    'message': f"发送失败: {result.get('msg', '未知错误')}",
                    'data': result
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'message': f"网络请求失败: {str(e)}",
                'data': None
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"发送消息时发生错误: {str(e)}",
                'data': None
            }
    
    def send_xhs_publish_notification(self, 
                                    xhs_account: str,
                                    image_count: int,
                                    image_paths: List[str],
                                    tweet_publish_time: str,
                                    tweet_content: str,
                                    tweet_author: str,
                                    max_image_size_kb: int = 100) -> Dict[str, Any]:
        """
        发送小红书发布通知
        
        Args:
            xhs_account: 小红书账户
            image_count: 图片数量
            image_paths: 图片URL列表（支持本地路径或网络URL）
            tweet_publish_time: 推文发布时间
            tweet_content: 推文内容
            tweet_author: 推文作者
            max_image_size_kb: 最大图片大小(KB)，已废弃，保留用于兼容性
            
        Returns:
            发送结果
        """
        # 构建富文本消息
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 截取推文内容
        content_preview = tweet_content[:100] + "..." if len(tweet_content) > 100 else tweet_content
        
        # 构建富文本内容
        rich_content = [
            [
                {"tag": "text", "text": f"📱 小红书账户: {xhs_account}"}
            ],
            [
                {"tag": "text", "text": f"👤 推文作者: @{tweet_author}"}
            ],
            [
                {"tag": "text", "text": f"📝 推文内容: {content_preview}"}
            ],
            [
                {"tag": "text", "text": f"📸 图片数量: {image_count} 张"}
            ],
            [
                {"tag": "text", "text": f"⏰ 推文发布时间: {tweet_publish_time}"}
            ],
            [
                {"tag": "text", "text": f"🕐 通知时间: {current_time}"}
            ]
        ]
        
        # 添加图片信息（如果有的话）
        if image_paths and len(image_paths) > 0:
            rich_content.append([
                {"tag": "text", "text": "🖼️ 图片链接:"}
            ])
            
            # 显示前3张图片的URL
            for i, image_url in enumerate(image_paths[:3], 1):
                try:
                    # 直接显示图片URL
                    rich_content.append([
                        {"tag": "text", "text": f"   图片{i}: "},
                        {"tag": "a", "text": "查看图片", "href": image_url}
                    ])
                except Exception as e:
                    rich_content.append([
                        {"tag": "text", "text": f"   图片{i}: {image_url}"}
                    ])
            
            if len(image_paths) > 3:
                rich_content.append([
                    {"tag": "text", "text": f"   ... 还有 {len(image_paths) - 3} 张图片"}
                ])
        
        return self.send_rich_text(
            title="🚀 小红书发布通知",
            content=rich_content
        )
    
    def send_simple_xhs_notification(self,
                                   xhs_account: str,
                                   image_count: int,
                                   tweet_author: str,
                                   tweet_publish_time: str) -> Dict[str, Any]:
        """
        发送简化的小红书发布通知
        
        Args:
            xhs_account: 小红书账户
            image_count: 图片数量
            tweet_author: 推文作者
            tweet_publish_time: 推文发布时间
            
        Returns:
            发送结果
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        message = f"""🚀 小红书发布通知

📱 小红书账户: {xhs_account}
👤 推文作者: @{tweet_author}
📸 图片数量: {image_count} 张
⏰ 推文发布时间: {tweet_publish_time}
🕐 通知时间: {current_time}

正在准备发布到小红书..."""

        return self.send_text(message)