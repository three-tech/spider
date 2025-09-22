# Base模块 - 基础配置和数据库管理

## 概述

Base模块是整个爬虫项目的基础设施模块，提供了数据库管理、配置管理、日志管理和通用工具函数等核心功能。

## 模块结构

```
base/
├── __init__.py          # 模块初始化，导出主要类
├── config.py           # 配置管理
├── database.py         # 数据库管理
├── logger.py           # 日志管理
├── utils.py            # 通用工具函数
└── README.md           # 本文档
```

## 核心功能

### 1. 配置管理 (config.py)

提供统一的配置管理功能：

```python
from base import BaseConfig

# 使用默认配置文件
config = BaseConfig()

# 使用自定义配置文件
config = BaseConfig('/path/to/config.json')

# 获取配置值
db_host = config.get('database.host', 'localhost')
log_level = config.get('logging.level', 'INFO')

# 设置配置值
config.set('spider.delay', 2)

# 获取专门的配置
db_config = config.get_database_config()
log_config = config.get_logging_config()
```

### 2. 数据库管理 (database.py)

提供MySQL数据库的连接和操作功能：

```python
from base import DatabaseManager

# 初始化数据库管理器
db = DatabaseManager()

# 执行查询
results = db.execute_query("SELECT * FROM users WHERE active = %s", (1,))

# 执行更新
db.execute_update("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))

# 批量插入
data = [{'name': 'Alice', 'email': 'alice@example.com'}, ...]
db.batch_insert('users', data)
```

### 3. 日志管理 (logger.py)

提供统一的日志管理功能：

```python
from base.logger import get_logger

# 获取日志记录器
logger = get_logger('my_module')

# 记录日志
logger.info('这是一条信息日志')
logger.error('这是一条错误日志')
logger.debug('这是一条调试日志')

# 使用自定义日志文件
logger = get_logger('my_module', 'logs/custom.log')
```

### 4. 通用工具 (utils.py)

提供各种通用工具函数：

```python
from base.utils import (
    ensure_dir, read_json, write_json, 
    get_timestamp, get_md5, safe_filename,
    retry_on_exception, chunk_list
)

# 确保目录存在
ensure_dir('data/output')

# JSON文件操作
data = read_json('config.json')
write_json(data, 'backup.json')

# 时间戳和哈希
timestamp = get_timestamp()
hash_value = get_md5('hello world')

# 安全文件名
filename = safe_filename('user@domain.com')

# 重试装饰器
@retry_on_exception(max_retries=3, delay=1.0)
def unstable_function():
    # 可能失败的函数
    pass

# 列表分块
chunks = chunk_list(range(100), 10)  # 分成10个一组
```

## 配置文件格式

默认配置文件 `config.json` 的格式：

```json
{
  "database": {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "spider_db",
    "charset": "utf8mb4"
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_path": "logs/spider.log"
  },
  "spider": {
    "delay": 1,
    "timeout": 30,
    "retry_times": 3,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  }
}
```

## 使用示例

### 完整的模块使用示例

```python
from base import DatabaseManager, BaseConfig
from base.logger import get_logger
from base.utils import ensure_dir, get_timestamp

# 初始化
config = BaseConfig()
db = DatabaseManager()
logger = get_logger('example')

# 确保数据目录存在
ensure_dir('data/output')

# 记录开始时间
start_time = get_timestamp()
logger.info(f'任务开始: {start_time}')

try:
    # 执行数据库操作
    results = db.execute_query("SELECT * FROM tweets LIMIT 10")
    logger.info(f'查询到 {len(results)} 条记录')
    
    # 处理数据...
    
except Exception as e:
    logger.error(f'任务执行失败: {e}')
finally:
    # 清理资源
    db.close()
    end_time = get_timestamp()
    logger.info(f'任务结束: {end_time}, 耗时: {end_time - start_time}秒')
```

## 依赖关系

Base模块是其他模块的基础，其他模块应该导入并使用base模块的功能：

- **x模块**: 使用base的数据库和配置管理
- **job模块**: 使用base的日志和工具函数
- **其他模块**: 根据需要使用base的各种功能

## 注意事项

1. **配置文件**: 确保项目根目录有正确的 `config.json` 文件
2. **数据库连接**: 确保数据库服务正常运行且配置正确
3. **日志目录**: 确保日志目录有写入权限
4. **导入路径**: 其他模块应该使用 `from base import ...` 的方式导入

## 扩展性

Base模块设计为可扩展的：

- 可以添加新的配置项
- 可以扩展数据库操作方法
- 可以添加新的工具函数
- 可以自定义日志格式和处理器