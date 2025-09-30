# SMS通知模块

## 📋 功能概述

SMS模块提供多种通知方式，目前支持飞书机器人通知。在小红书自动发布任务中，会在发布前发送通知到飞书群，包含以下信息：

- 当前登录的小红书账户
- 要发送的图片数量和链接
- 转发推文的发布时间
- 推文内容和作者信息

## 🏗️ 模块结构

```
sms/
├── __init__.py              # 模块初始化
├── feishu_bot.py           # 飞书机器人核心功能
├── config.py               # 配置管理
├── notification_manager.py  # 通知管理器
├── test_feishu_notification.py  # 测试脚本
└── README.md               # 说明文档
```

## ⚙️ 配置设置

在项目根目录的 `config.json` 文件中添加SMS配置：

```json
{
  "sms": {
    "feishu": {
      "enabled": true,
      "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-url-here",
      "secret": "your-secret-if-needed"
    }
  }
}
```

### 配置说明

- `enabled`: 是否启用飞书通知
- `webhook_url`: 飞书机器人的Webhook地址
- `secret`: 机器人密钥（可选，用于签名验证）

## 🤖 飞书机器人设置

### 1. 创建飞书机器人

1. 在飞书群中添加机器人
2. 选择"自定义机器人"
3. 设置机器人名称和描述
4. 获取Webhook地址
5. （可选）设置安全设置中的签名校验

### 2. 获取Webhook地址

飞书机器人创建后会提供一个Webhook地址，格式如下：
```
https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxxx
```

将此地址配置到 `config.json` 中的 `webhook_url` 字段。

## 🚀 使用方法

### 基础使用

```python
from sms.notification_manager import get_notification_manager

# 获取通知管理器
notification_manager = get_notification_manager()

# 发送小红书发布通知
result = notification_manager.send_xhs_publish_notification(
    xhs_account="your_xhs_account",
    image_count=3,
    image_urls=["url1", "url2", "url3"],
    tweet_publish_time="2025-09-21 17:00:00",
    tweet_content="推文内容...",
    tweet_author="twitter_user"
)

if result['feishu']['success']:
    print("通知发送成功")
else:
    print(f"通知发送失败: {result['feishu']['message']}")
```

### 集成到发布流程

SMS模块已自动集成到小红书发布任务中（`job/tasks.py`），在发布前会自动发送通知。

## 📤 通知消息格式

### 完整通知消息

飞书通知包含以下信息：

```
🚀 小红书发布通知

📱 小红书账户: your_xhs_account
👤 推文作者: @twitter_user
📝 推文内容: 这是推文内容的预览...
📸 图片数量: 3 张
⏰ 推文发布时间: 2025-09-21 17:00:00
🕐 通知时间: 2025-09-21 17:05:00
🔗 图片链接:
   1. 图片1
   2. 图片2
   3. 图片3
```

### 简化通知消息

```
🚀 小红书发布通知

📱 小红书账户: your_xhs_account
👤 推文作者: @twitter_user
📸 图片数量: 3 张
⏰ 推文发布时间: 2025-09-21 17:00:00
🕐 通知时间: 2025-09-21 17:05:00

正在准备发布到小红书...
```

## 🧪 测试功能

### 1. 测试飞书通知

```bash
cd sms
python test_feishu_notification.py
```

### 2. 演示完整流程

```bash
cd job
python demo_xhs_with_feishu_notification.py
```

## 🔧 API参考

### FeishuBot 类

#### 主要方法

- `send_text(text)`: 发送纯文本消息
- `send_rich_text(title, content)`: 发送富文本消息
- `send_xhs_publish_notification(...)`: 发送小红书发布通知

### NotificationManager 类

#### 主要方法

- `send_xhs_publish_notification(...)`: 发送完整的小红书发布通知
- `send_simple_notification(...)`: 发送简化通知
- `is_notification_enabled()`: 检查通知是否启用

## 🔒 安全特性

1. **签名验证**: 支持飞书机器人的签名校验
2. **配置验证**: 自动检查配置的有效性
3. **错误处理**: 完善的异常处理机制
4. **日志记录**: 详细的操作日志

## 🐛 故障排除

### 常见问题

1. **通知发送失败**
   - 检查webhook_url是否正确
   - 确认机器人是否已添加到群中
   - 验证网络连接

2. **配置未生效**
   - 确认config.json格式正确
   - 检查enabled字段是否为true
   - 重启应用程序

3. **签名验证失败**
   - 确认secret配置正确
   - 检查时间同步

### 调试方法

1. 启用详细日志
2. 使用测试脚本验证配置
3. 检查飞书机器人状态

## 📈 扩展功能

SMS模块设计为可扩展架构，未来可以添加：

- 钉钉机器人支持
- 企业微信通知
- 邮件通知
- 短信通知
- Slack集成

## 🔄 更新日志

### v1.0.0 (2025-09-21)
- ✅ 实现飞书机器人基础功能
- ✅ 集成到小红书发布流程
- ✅ 支持富文本和卡片消息
- ✅ 添加配置管理和错误处理
- ✅ 创建测试和演示脚本