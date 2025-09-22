# X平台（Twitter）爬虫系统

一个高效的X平台推文爬虫系统，支持自动获取指定用户的推文数据并保存到MySQL数据库。

## ✨ 功能特性

- 🔐 **安全认证**：基于Cookie的X平台认证，完全模拟浏览器行为
- 📊 **数据完整**：获取推文的完整信息（文本、图片、视频、链接、时间等）
- 🗄️ **数据库存储**：自动保存到MySQL数据库，支持批量插入
- 📁 **JSON备份**：同时生成JSON格式的数据备份
- ⚡ **高效稳定**：智能分页、请求限制、错误重试机制
- 🎯 **精准过滤**：支持转发过滤、时间范围等多种筛选条件

## 📋 获取字段

| 字段名 | 描述 | 示例 |
|--------|------|------|
| `screenName` | 用户名 | `@elonmusk` |
| `images` | 图片链接 | `https://pbs.twimg.com/media/xxx.jpg` |
| `videos` | 视频链接 | `https://video.twimg.com/xxx.mp4` |
| `tweetUrl` | 推文链接 | `https://x.com/elonmusk/status/123` |
| `fullText` | 推文完整文本 | `Hello World!` |
| `publishTime` | 发布时间 | `2024-12-09 10:30:00` |

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd x

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库配置

创建MySQL数据库和表：

```sql
-- 创建数据库
CREATE DATABASE resource;
USE resource;

-- 创建推文表
CREATE TABLE `resource_x` (
  `id` int NOT NULL AUTO_INCREMENT,
  `screenName` varchar(255) DEFAULT NULL COMMENT '用户名',
  `images` text COMMENT '图片链接，逗号分隔',
  `videos` text COMMENT '视频链接，逗号分隔',
  `tweetUrl` varchar(500) DEFAULT NULL COMMENT '推文链接',
  `fullText` text COMMENT '推文完整文本',
  `publishTime` datetime DEFAULT NULL COMMENT '发布时间',
  `create_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_screen_name` (`screenName`),
  KEY `idx_publish_time` (`publishTime`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='X平台推文数据表';
```

### 3. 获取认证Token

#### 方法1：浏览器手动获取（推荐）

1. 登录 [X.com](https://x.com)
2. 按 `F12` 打开开发者工具
3. 切换到 `Application` → `Cookies` → `https://x.com`
4. 复制 `auth_token` 的值
5. 将token填入 `config.json` 的 `api.auth_token` 字段

#### 方法2：配置示例

```json
{
  "api": {
    "auth_token": "你的真实auth_token"
  }
}
```

### 4. 配置爬取参数

编辑 `config.json`：

```json
{
  "users": ["elonmusk", "OpenAI", "你要爬取的用户名"],
  "settings": {
    "include_retweets": false,
    "max_tweets": 200,
    "delay_seconds": 5
  },
  "database": {
    "host": "localhost",
    "user": "root", 
    "password": "123456",
    "database": "resource"
  }
}
```

### 5. 运行爬虫

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行爬虫
python x_spider_optimized.py
```

## 📁 项目结构

```
x/
├── x_spider_optimized.py    # 主爬虫程序
├── x_auth_client.py         # X平台认证客户端
├── database.py              # 数据库操作模块
├── config.json              # 配置文件
├── requirements.txt         # Python依赖
└── README.md               # 项目说明
```

## ⚙️ 配置说明

### config.json 详细配置

```json
{
  "users": [
    "elonmusk",           // 要爬取的用户名列表
    "OpenAI"
  ],
  "settings": {
    "include_retweets": false,    // 是否包含转发
    "max_tweets": 200,            // 最大爬取数量
    "delay_seconds": 5,           // 请求间隔（秒）
    "start_date": "2024-01-01",   // 开始日期（可选）
    "end_date": "2024-12-31"      // 结束日期（可选）
  },
  "database": {
    "host": "localhost",          // 数据库地址
    "port": 3306,                // 数据库端口
    "user": "root",              // 数据库用户名
    "password": "123456",        // 数据库密码
    "database": "resource"       // 数据库名
  },
  "api": {
    "auth_token": "你的auth_token"  // X平台认证token
  }
}
```

## 🔧 高级功能

### 1. 批量用户爬取

```json
{
  "users": ["user1", "user2", "user3"],
  "settings": {
    "max_tweets": 100
  }
}
```

### 2. 时间范围过滤

```json
{
  "settings": {
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }
}
```

### 3. 数据备份

爬虫会自动在 `../data/x/` 目录生成JSON备份文件。

## 📊 运行示例

```bash
$ python x_spider_optimized.py

2024-12-09 10:30:00 - INFO - 🚀 开始爬取用户: @elonmusk
2024-12-09 10:30:01 - INFO - ✅ 认证成功，获取到CSRF token
2024-12-09 10:30:02 - INFO - 👤 用户信息: @elonmusk (ID: 44196397)
2024-12-09 10:30:03 - INFO - 🔄 获取到 20 条推文
2024-12-09 10:30:03 - INFO - ✅ 转换成功: https://x.com/elonmusk/status/123
...
2024-12-09 10:35:00 - INFO - 📊 准备插入数据库的数据量: 199 条
2024-12-09 10:35:01 - INFO - ✅ 成功保存 199 条推文到数据库
2024-12-09 10:35:01 - INFO - 🎉 处理完成！共处理 199 条推文
```

## ⚠️ 注意事项

1. **Token有效性**：auth_token会过期，需要定期更新
2. **请求频率**：建议保持5秒间隔，避免被限制
3. **数据库权限**：确保MySQL用户有创建表和插入数据的权限
4. **网络环境**：需要能正常访问X.com的网络环境

## 🐛 常见问题

### Q: 403认证错误
A: 检查auth_token是否有效，重新从浏览器获取

### Q: 数据库连接失败
A: 检查数据库配置和权限，确保MySQL服务正在运行

### Q: 获取不到推文
A: 检查用户名是否正确，用户是否设置了隐私保护

### Q: 推文数量不足
A: 用户可能推文较少，或者设置了时间范围过滤

## 📄 许可证

本项目仅供学习和研究使用，请遵守X平台的使用条款和相关法律法规。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

---

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！**