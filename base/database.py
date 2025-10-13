#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SQLite数据库管理模块
纯净的SQLite实现，无MySQL依赖
"""

import sqlite3
import threading
import time
import os
import json
import logging
from contextlib import contextmanager
from typing import Dict, List, Tuple, Any, Optional, Union
from pathlib import Path
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SQLiteConnectionPool:
    """SQLite连接池管理器"""
    
    def __init__(self, database_path: str, max_connections: int = 10):
        """
        初始化SQLite连接池
        
        Args:
            database_path: SQLite数据库文件路径
            max_connections: 最大连接数
        """
        self.database_path = database_path
        self.max_connections = max_connections
        self._connections = []
        self._lock = threading.Lock()
        self._create_database_if_not_exists()
    
    def _create_database_if_not_exists(self):
        """创建数据库目录和文件（如果不存在）"""
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        with self._lock:
            if self._connections:
                return self._connections.pop()
            else:
                conn = sqlite3.connect(
                    self.database_path,
                    check_same_thread=False,
                    timeout=30.0
                )
                # 启用外键约束
                conn.execute("PRAGMA foreign_keys = ON")
                # 设置WAL模式以提高并发性能
                conn.execute("PRAGMA journal_mode = WAL")
                # 设置行格式返回
                conn.row_factory = sqlite3.Row
                return conn
    
    def return_connection(self, conn: sqlite3.Connection):
        """归还数据库连接"""
        with self._lock:
            if len(self._connections) < self.max_connections:
                self._connections.append(conn)
            else:
                conn.close()
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for conn in self._connections:
                conn.close()
            self._connections.clear()

class DatabaseConfig:
    """数据库配置类"""
    
    # 数据库文件路径配置
    DATABASE_PATHS = {
        'spider': 'data/spider.db',
        'x': 'data/x.db', 
        'xiaohongshu': 'data/xiaohongshu.db',
        'zhiwang': 'data/zhiwang.db',
        'job': 'data/job.db',
        'telegram': 'data/telegram.db',
        'resource': 'data/spider.db'  # 兼容性映射
    }
    
    @classmethod
    def get_database_path(cls, db_name: str) -> str:
        """获取数据库文件路径"""
        return cls.DATABASE_PATHS.get(db_name, f'data/{db_name}.db')

# 全局连接池实例
_connection_pools: Dict[str, SQLiteConnectionPool] = {}
_pool_lock = threading.Lock()

def get_connection_pool(db_name: str) -> SQLiteConnectionPool:
    """获取指定数据库的连接池"""
    with _pool_lock:
        if db_name not in _connection_pools:
            db_path = DatabaseConfig.get_database_path(db_name)
            _connection_pools[db_name] = SQLiteConnectionPool(db_path)
        return _connection_pools[db_name]

@contextmanager
def get_db_connection(db_name: str = 'spider'):
    """
    获取数据库连接的上下文管理器
    
    Args:
        db_name: 数据库名称
        
    Yields:
        sqlite3.Connection: 数据库连接对象
    """
    pool = get_connection_pool(db_name)
    conn = pool.get_connection()
    try:
        yield conn
    finally:
        pool.return_connection(conn)

@contextmanager
def get_db_cursor(db_name: str = 'spider', commit: bool = True):
    """
    获取数据库游标的上下文管理器
    
    Args:
        db_name: 数据库名称
        commit: 是否自动提交事务
        
    Yields:
        sqlite3.Cursor: 数据库游标对象
    """
    with get_db_connection(db_name) as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_name: str = 'spider'):
        """
        初始化数据库管理器
        
        Args:
            db_name: 数据库名称
        """
        # 兼容性处理
        if db_name == 'resource':
            db_name = 'spider'
        
        self.db_name = db_name
        self.pool = get_connection_pool(db_name)
    
    def execute_query(self, sql: str, params: Tuple[Any, ...] = None) -> List[sqlite3.Row]:
        """
        执行查询SQL
        
        Args:
            sql: SQL语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        with get_db_cursor(self.db_name, commit=False) as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
    
    def execute_update(self, sql: str, params: Tuple[Any, ...] = None) -> int:
        """
        执行更新SQL
        
        Args:
            sql: SQL语句
            params: 更新参数
            
        Returns:
            受影响的行数
        """
        with get_db_cursor(self.db_name) as cursor:
            cursor.execute(sql, params or ())
            return cursor.rowcount
    
    def execute_many(self, sql: str, params_list: List[Tuple[Any, ...]]) -> int:
        """
        批量执行SQL
        
        Args:
            sql: SQL语句
            params_list: 参数列表
            
        Returns:
            总受影响行数
        """
        with get_db_cursor(self.db_name) as cursor:
            cursor.executemany(sql, params_list)
            return cursor.rowcount
    
    def get_last_insert_id(self) -> Optional[int]:
        """获取最后插入记录的ID"""
        with get_db_cursor(self.db_name, commit=False) as cursor:
            return cursor.lastrowid
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        sql = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
        """
        result = self.execute_query(sql, (table_name,))
        return len(result) > 0
    
    def create_table_if_not_exists(self, table_name: str, table_sql: str):
        """如果表不存在则创建"""
        if not self.table_exists(table_name):
            self.execute_update(table_sql)
            logger.info(f"Created table: {table_name}")
    
    # 兼容性方法
    def setup_database(self):
        """设置数据库连接（兼容性方法）"""
        pass
    
    def save_tweet(self, tweet_data: Dict[str, Any]) -> bool:
        """保存推文数据（兼容性方法）"""
        try:
            sql = """
            INSERT OR REPLACE INTO x_tweets 
            (tweet_id, user_id, content, created_at, retweet_count, like_count, reply_count) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                tweet_data.get('tweet_id'),
                tweet_data.get('user_id'),
                tweet_data.get('content', ''),
                tweet_data.get('created_at'),
                tweet_data.get('retweet_count', 0),
                tweet_data.get('like_count', 0),
                tweet_data.get('reply_count', 0)
            )
            self.execute_update(sql, params)
            return True
        except Exception as e:
            logger.error(f"Failed to save tweet: {e}")
            return False
    
    def save_member(self, member_data: Dict[str, Any]) -> bool:
        """保存用户数据（兼容性方法）"""
        try:
            sql = """
            INSERT OR REPLACE INTO x_users 
            (user_id, username, display_name, followers_count, following_count) 
            VALUES (?, ?, ?, ?, ?)
            """
            params = (
                member_data.get('user_id'),
                member_data.get('username'),
                member_data.get('display_name', ''),
                member_data.get('followers_count', 0),
                member_data.get('following_count', 0)
            )
            self.execute_update(sql, params)
            return True
        except Exception as e:
            logger.error(f"Failed to save member: {e}")
            return False
    
    def get_tweet_count(self) -> int:
        """获取推文总数（兼容性方法）"""
        try:
            result = self.execute_query("SELECT COUNT(*) as count FROM x_tweets")
            return result[0]['count'] if result else 0
        except:
            return 0
    
    def get_member_count(self) -> int:
        """获取用户总数（兼容性方法）"""
        try:
            result = self.execute_query("SELECT COUNT(*) as count FROM x_users")
            return result[0]['count'] if result else 0
        except:
            return 0

# 表结构定义 - 适配SQLite语法
TABLE_DEFINITIONS = {
    # X平台相关表
    'x_users': '''
        CREATE TABLE IF NOT EXISTS x_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            username TEXT,
            display_name TEXT,
            description TEXT,
            followers_count INTEGER DEFAULT 0,
            following_count INTEGER DEFAULT 0,
            tweets_count INTEGER DEFAULT 0,
            verified INTEGER DEFAULT 0,
            profile_image_url TEXT,
            banner_url TEXT,
            location TEXT,
            website TEXT,
            created_at TEXT,
            updated_at TEXT DEFAULT (datetime('now')),
            status INTEGER DEFAULT 1
        )
    ''',
    
    'x_tweets': '''
        CREATE TABLE IF NOT EXISTS x_tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            content TEXT,
            created_at TEXT,
            retweet_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            reply_count INTEGER DEFAULT 0,
            quote_count INTEGER DEFAULT 0,
            lang TEXT,
            source TEXT,
            in_reply_to_tweet_id TEXT,
            in_reply_to_user_id TEXT,
            is_retweet INTEGER DEFAULT 0,
            retweeted_tweet_id TEXT,
            media_urls TEXT,
            hashtags TEXT,
            mentions TEXT,
            urls TEXT,
            updated_at TEXT DEFAULT (datetime('now')),
            status INTEGER DEFAULT 1
        )
    ''',
    
    'x_media': '''
        CREATE TABLE IF NOT EXISTS x_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_id TEXT UNIQUE NOT NULL,
            tweet_id TEXT NOT NULL,
            media_type TEXT,
            media_url TEXT,
            preview_image_url TEXT,
            alt_text TEXT,
            width INTEGER,
            height INTEGER,
            duration INTEGER,
            size INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            status INTEGER DEFAULT 1
        )
    ''',
    
    # 小红书相关表
    'xiaohongshu_users': '''
        CREATE TABLE IF NOT EXISTS xiaohongshu_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            nickname TEXT,
            avatar_url TEXT,
            description TEXT,
            followers_count INTEGER DEFAULT 0,
            following_count INTEGER DEFAULT 0,
            likes_count INTEGER DEFAULT 0,
            notes_count INTEGER DEFAULT 0,
            verified INTEGER DEFAULT 0,
            verification_info TEXT,
            location TEXT,
            gender TEXT,
            age INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            status INTEGER DEFAULT 1
        )
    ''',
    
    'xiaohongshu_notes': '''
        CREATE TABLE IF NOT EXISTS xiaohongshu_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            title TEXT,
            content TEXT,
            note_type TEXT,
            created_at TEXT,
            likes_count INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            shares_count INTEGER DEFAULT 0,
            views_count INTEGER DEFAULT 0,
            tags TEXT,
            topics TEXT,
            location TEXT,
            media_urls TEXT,
            updated_at TEXT DEFAULT (datetime('now')),
            status INTEGER DEFAULT 1
        )
    ''',
    
    # 知网相关表
    'zhiwang_papers': '''
        CREATE TABLE IF NOT EXISTS zhiwang_papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            authors TEXT,
            abstract TEXT,
            keywords TEXT,
            journal TEXT,
            publish_date TEXT,
            doi TEXT,
            citation_count INTEGER DEFAULT 0,
            download_count INTEGER DEFAULT 0,
            subject_category TEXT,
            fund_info TEXT,
            pdf_url TEXT,
            html_url TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            status INTEGER DEFAULT 1
        )
    ''',
    
    # 任务管理表
    'job_tasks': '''
        CREATE TABLE IF NOT EXISTS job_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            task_name TEXT NOT NULL,
            task_type TEXT NOT NULL,
            target_platform TEXT,
            parameters TEXT,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 0,
            created_by TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            started_at TEXT,
            completed_at TEXT,
            error_message TEXT,
            result_data TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    ''',
    
    'job_logs': '''
        CREATE TABLE IF NOT EXISTS job_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            log_level TEXT DEFAULT 'INFO',
            message TEXT NOT NULL,
            details TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''',
    
    # Telegram机器人相关表
    'telegram_users': '''
        CREATE TABLE IF NOT EXISTS telegram_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language_code TEXT DEFAULT 'zh',
            is_bot INTEGER DEFAULT 0,
            is_premium INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            status INTEGER DEFAULT 1
        )
    ''',
    
    'telegram_messages': '''
        CREATE TABLE IF NOT EXISTS telegram_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            message_type TEXT DEFAULT 'text',
            content TEXT,
            file_id TEXT,
            file_path TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''',
    
    # 通用配置表
    'system_config': '''
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT,
            config_type TEXT DEFAULT 'string',
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    ''',
    
    # 代理IP管理表
    'proxy_ips': '''
        CREATE TABLE IF NOT EXISTS proxy_ips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            port INTEGER NOT NULL,
            username TEXT,
            password TEXT,
            proxy_type TEXT DEFAULT 'http',
            country TEXT,
            region TEXT,
            speed_ms INTEGER,
            success_rate REAL DEFAULT 1.0,
            last_used TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(ip, port)
        )
    ''',
    
    # Cookies管理表
    'cookies_storage': '''
        CREATE TABLE IF NOT EXISTS cookies_storage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            account TEXT,
            cookies_data TEXT,
            user_agent TEXT,
            is_valid INTEGER DEFAULT 1,
            expires_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(platform, account)
        )
    '''
}

def initialize_database(db_name: str = 'spider'):
    """
    初始化数据库，创建所有必要的表
    
    Args:
        db_name: 数据库名称
    """
    # 兼容性处理
    if db_name == 'resource':
        db_name = 'spider'
    
    db_manager = DatabaseManager(db_name)
    
    # 根据数据库名称创建相应的表
    tables_to_create = []
    
    if db_name == 'x':
        tables_to_create = ['x_users', 'x_tweets', 'x_media']
    elif db_name == 'xiaohongshu':
        tables_to_create = ['xiaohongshu_users', 'xiaohongshu_notes']
    elif db_name == 'zhiwang':
        tables_to_create = ['zhiwang_papers']
    elif db_name == 'job':
        tables_to_create = ['job_tasks', 'job_logs']
    elif db_name == 'telegram':
        tables_to_create = ['telegram_users', 'telegram_messages']
    else:
        # 默认spider数据库包含所有表
        tables_to_create = list(TABLE_DEFINITIONS.keys())
    
    for table_name in tables_to_create:
        if table_name in TABLE_DEFINITIONS:
            db_manager.create_table_if_not_exists(table_name, TABLE_DEFINITIONS[table_name])
    
    logger.info(f"Database '{db_name}' initialized successfully")

# 便捷函数
def get_spider_db() -> DatabaseManager:
    """获取爬虫主数据库管理器"""
    return DatabaseManager('spider')

def get_x_db() -> DatabaseManager:
    """获取X平台数据库管理器"""
    return DatabaseManager('x')

def get_xiaohongshu_db() -> DatabaseManager:
    """获取小红书数据库管理器"""
    return DatabaseManager('xiaohongshu')

def get_zhiwang_db() -> DatabaseManager:
    """获取知网数据库管理器"""
    return DatabaseManager('zhiwang')

def get_job_db() -> DatabaseManager:
    """获取任务管理数据库管理器"""
    return DatabaseManager('job')

def get_telegram_db() -> DatabaseManager:
    """获取Telegram机器人数据库管理器"""
    return DatabaseManager('telegram')

# 初始化所有数据库
def initialize_all_databases():
    """初始化项目中的所有数据库"""
    databases = ['spider', 'x', 'xiaohongshu', 'zhiwang', 'job', 'telegram']
    for db_name in databases:
        try:
            initialize_database(db_name)
        except Exception as e:
            logger.error(f"Failed to initialize database '{db_name}': {e}")

# 清理资源
def cleanup_all_connections():
    """清理所有数据库连接"""
    with _pool_lock:
        for pool in _connection_pools.values():
            pool.close_all()
        _connection_pools.clear()

if __name__ == "__main__":
    # 测试数据库连接和表创建
    initialize_all_databases()
    
    # 测试基本操作
    db = get_spider_db()
    
    # 插入测试配置
    test_config_sql = """
    INSERT OR REPLACE INTO system_config (config_key, config_value, description) 
    VALUES (?, ?, ?)
    """
    db.execute_update(test_config_sql, ('database_type', 'sqlite', 'Database type configuration'))
    
    # 查询测试
    configs = db.execute_query("SELECT * FROM system_config WHERE config_key = ?", ('database_type',))
    if configs:
        logger.info(f"Test successful: {dict(configs[0])}")
    
    # 清理连接
    cleanup_all_connections()
    logger.info("Database migration to SQLite completed successfully!")