# Telegram Bot 模块

基于 Python-Telegram-Bot 框架的内容推送机器人，负责将资源内容自动推送到订阅的 Telegram 群组。

## 📋 功能特性

- ✅ **自动内容推送**: 根据订阅关系定时推送最新内容
- ✅ **多群组管理**: 支持多个群组订阅不同标签的内容
- ✅ **进度跟踪**: 记录每个订阅的推送进度，避免重复推送
- ✅ **状态报告**: 定期向管理员发送运行状态报告
- ✅ **命令交互**: 支持基本的命令交互功能
- ✅ **配置管理**: 灵活的配置管理系统

## 🏗️ 架构设计

### 核心模块

```
telegram/
├── main.py              # 主入口点
├── bot.py              # 机器人核心类
├── config.py           # 配置管理
├── database.py         # 数据库操作
├── scheduler.py        # 任务调度器
├── handlers.py         # 命令和消息处理器
├── utils.py           # 工具函数
├── exceptions.py      # 自定义异常
└── __init__.py        # 模块初始化
```

### 数据模型

#### 1. `telegram_settings` (配置表)
- **用途**: 存储所有动态配置（管理员、广告、全局设置等）
- **字段**:
  - `id`: 主键ID
  - `type`: 配置类型（admin, ad, ad_strategy, global_setting）
  - `config`: 配置内容（JSON格式）
  - `created_at`: 创建时间
  - `updated_at`: 更新时间

#### 2. `telegram_subscriptions` (订阅与进度表)
- **用途**: 存储群组订阅关系和推送进度
- **字段**:
  - `chat_id`: Telegram群组ID（主键）
  - `tag`: 订阅的内容标签（主键）
  - `last_resource_x_id`: 最后推送的资源ID
  - `is_active`: 是否激活
  - `created_at`: 创建时间
  - `updated_at`: 更新时间

## 🚀 快速开始

### 1. 环境准备

```bash
# 激活conda环境
conda activate spider

# 安装依赖
pip install -r telegram/requirements.txt
```

### 2. 配置设置

在 `config.toml` 中添加 Telegram 配置：

```toml
[telegram]
bot_token = "YOUR_BOT_TOKEN"

[telegram.database]
host = "localhost"
port = 3306
user = "root"
password = "your_password"
database = "resource"
```

### 3. 运行测试

```bash
python telegram/test_main.py
```

### 4. 启动机器人

```bash
python telegram/main.py
```

## 📝 使用说明

### 可用命令

- `/start` - 启动机器人
- `/help` - 查看帮助信息  
- `/status` - 查看机器人状态

### 订阅管理

1. **添加订阅**: 在 `telegram_subscriptions` 表中添加记录
2. **配置标签**: 设置群组订阅的内容标签
3. **激活订阅**: 设置 `is_active = 1`

### 管理员配置

在 `telegram_settings` 表中添加管理员：

```sql
INSERT INTO telegram_settings (type, config, created_at, updated_at)
VALUES ('admin', '{"user_id": 123456789, "name": "管理员"}', NOW(), NOW());
```

## 🔧 开发指南

### 代码规范

- 遵循 **PEP 8** 编码规范
- 使用类型注解提高代码可读性
- 函数长度不超过 **80 行**
- 圈复杂度不超过 **10**

### 错误处理

使用自定义异常类进行错误处理：

```python
from telegram.exceptions import ConfigError, DatabaseError

try:
    # 业务逻辑
    pass
except ConfigError as e:
    logger.error(f"配置错误: {e}")
except DatabaseError as e:
    logger.error(f"数据库错误: {e}")
```

### 日志记录

使用统一的日志系统：

```python
from base.logger import get_logger

logger = get_logger(__name__)
logger.info("操作日志")
logger.error("错误日志")
```

## 📊 监控与维护

### 状态监控

- 机器人运行状态
- 订阅数量统计
- 推送成功率
- 错误率监控

### 维护任务

- 定期清理过期数据
- 备份关键配置
- 更新依赖版本

## 🐛 故障排除

### 常见问题

1. **导入错误**: 检查 Python 路径和依赖安装
2. **配置错误**: 验证 `config.toml` 文件格式
3. **数据库连接失败**: 检查数据库配置和网络连接
4. **权限不足**: 确认机器人有发送消息的权限

### 调试模式

启用详细日志进行调试：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📄 许可证

本项目遵循项目主许可证。

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request 来改进这个模块。