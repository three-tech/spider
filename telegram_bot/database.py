"""
Telegram机器人数据库管理器

负责所有与Telegram机器人相关的数据库操作，包括表结构管理和数据访问
"""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, JSON, Boolean, select
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.exc import SQLAlchemyError

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.database import DatabaseManager as BaseDatabaseManager
from base.logger import get_logger


# 使用独立的Base以避免与其他模块的表定义冲突
Base = declarative_base()
logger = get_logger("telegram_database")


class TelegramSettings(Base):
    """
    telegram_settings表模型 (EAV - 实体-属性-值模型)
    
    用于存储所有动态配置，如管理员列表、广告、全局设置等
    """
    __tablename__ = "telegram_settings"
    __table_args__ = {"schema": "resource", "comment": "Telegram机器人动态配置表"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    type = Column(String(50), nullable=False, index=True, comment="配置类型")
    config = Column(JSON, nullable=False, comment="配置内容(JSON格式)")
    created_at = Column(DateTime, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, comment="更新时间")


class TelegramSubscriptions(Base):
    """
    telegram_subscriptions表模型
    
    存储群组对特定标签的订阅关系以及推送进度
    """
    __tablename__ = "telegram_subscriptions"
    __table_args__ = {"schema": "resource", "comment": "Telegram机器人订阅与推送进度表"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    chat_id = Column(BigInteger, nullable=False, index=True, comment="Telegram群组ID")
    tag = Column(String(100), nullable=False, index=True, comment="订阅的内容标签")
    last_resource_x_id = Column(Integer, default=0, comment="最后推送的资源ID")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, comment="更新时间")
    
    def __repr__(self):
        return f"<TelegramSubscription(chat_id={self.chat_id}, tag='{self.tag}', last_id={self.last_resource_x_id})>"


class TelegramDatabaseManager:
    """Telegram机器人专属数据库管理器"""
    
    def __init__(self, telegram_config: Dict[str, Any] = None):
        """
        初始化数据库管理器
        
        Args:
            telegram_config: Telegram相关配置（可选，如果为None则使用默认数据库配置）
        """
        # 使用默认数据库配置或提供的配置
        if telegram_config is None:
            # 默认数据库配置
            database_config = {
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "123456",
                "database": "resource"
            }
        else:
            database_config = telegram_config.get("database", {})
            
        self.base_db_manager = BaseDatabaseManager(config=database_config)
        self.Session = self.base_db_manager.Session
        self.engine = self.base_db_manager.engine

    def init_database(self) -> None:
        """初始化数据库表结构"""
        try:
            logger.info("正在检查并创建Telegram相关数据表...")
            Base.metadata.create_all(self.engine)
            logger.info("✅ 数据表检查与创建完成")
        except Exception as error:
            logger.error(f"创建数据表失败: {error}", exc_info=True)
            raise

    def get_settings_by_type(self, setting_type: str) -> List[Dict[str, Any]]:
        """
        根据类型获取所有配置
        
        Args:
            setting_type: 配置类型
            
        Returns:
            匹配的配置字典列表
        """
        session = self.Session()
        try:
            settings = session.query(TelegramSettings).filter_by(type=setting_type).all()
            return [setting.config for setting in settings]
        except Exception as error:
            logger.error(f"获取类型'{setting_type}'的配置失败: {error}", exc_info=True)
            return []
        finally:
            session.close()

    def get_all_subscriptions(self) -> List[TelegramSubscriptions]:
        """
        获取所有活跃的订阅记录
        
        Returns:
            订阅记录对象列表
        """
        session = self.Session()
        try:
            return session.query(TelegramSubscriptions).filter_by(is_active=True).all()
        except Exception as error:
            logger.error(f"获取所有订阅记录失败: {error}", exc_info=True)
            return []
        finally:
            session.close()

    def get_new_content_for_subscription(self, subscription: TelegramSubscriptions) -> List[Dict[str, Any]]:
        """
        根据订阅关系获取新的内容
        
        Args:
            subscription: 订阅记录对象
            
        Returns:
            新内容字典列表
        """
        session = self.Session()
        try:
            # 查询ResourceX表中符合条件的最新内容
            query = """
                SELECT id, fullText, images, videos, tags, publishTime 
                FROM resource.resource_x 
                WHERE id > :last_id 
                AND (tags LIKE :tag_pattern OR fullText LIKE :tag_pattern)
                ORDER BY id ASC 
                LIMIT 10
            """
            
            results = session.execute(
                query, 
                {
                    'last_id': subscription.last_resource_x_id,
                    'tag_pattern': f'%{subscription.tag}%'
                }
            ).fetchall()
            
            resources = []
            for result in results:
                resources.append({
                    'id': result[0],
                    'content': result[1],
                    'images': result[2],
                    'videos': result[3],
                    'tags': result[4],
                    'publish_time': result[5]
                })
            
            return resources
            
        except Exception as error:
            logger.error(f"获取新内容失败: {error}", exc_info=True)
            return []
        finally:
            session.close()

    def add_subscription(self, chat_id: int, tag: str) -> bool:
        """
        添加新的订阅关系
        
        Args:
            chat_id: 群组ID
            tag: 标签
            
        Returns:
            操作是否成功
        """
        session = self.Session()
        try:
            # 检查是否已存在相同订阅
            existing = session.query(TelegramSubscriptions).filter_by(
                chat_id=chat_id, tag=tag
            ).first()
            
            if existing:
                logger.warning(f"订阅关系已存在: chat_id={chat_id}, tag='{tag}'")
                return False
                
            from datetime import datetime
            subscription = TelegramSubscriptions(
                chat_id=chat_id,
                tag=tag,
                last_resource_x_id=0,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            session.add(subscription)
            session.commit()
            logger.info(f"✅ 成功添加订阅: chat_id={chat_id}, tag='{tag}'")
            return True
            
        except Exception as error:
            session.rollback()
            logger.error(f"添加订阅失败: {error}", exc_info=True)
            return False
        finally:
            session.close()

    def get_admins(self) -> List[int]:
        """
        获取所有管理员用户ID
        
        Returns:
            管理员用户ID列表
        """
        try:
            # 从数据库读取管理员配置
            admin_settings = self.get_settings_by_type("admin_config")
            if not admin_settings:
                logger.warning("未在数据库中找到管理员配置")
                return []
            
            # 解析管理员ID列表
            admin_config = admin_settings[0]
            admin_ids = admin_config.get("admin_ids", [])
            return [int(admin_id) for admin_id in admin_ids] if admin_ids else []
        except Exception as error:
            logger.error(f"获取管理员ID失败: {error}", exc_info=True)
            return []

    def get_alert_channel_id(self) -> Optional[int]:
        """
        获取警报频道ID
        
        Returns:
            频道ID或None
        """
        try:
            # 从数据库读取频道配置
            channel_settings = self.get_settings_by_type("channel_config")
            if not channel_settings:
                logger.warning("未在数据库中找到频道配置")
                return None
            
            # 解析频道ID
            channel_config = channel_settings[0]
            return channel_config.get("alert_channel_id")
        except Exception as error:
            logger.error(f"获取警报频道ID失败: {error}", exc_info=True)
            return None

    def update_subscription_progress(self, chat_id: int, tag: str, 
                                   last_resource_x_id: int) -> bool:
        """
        更新特定订阅的推送进度
        
        Args:
            chat_id: 群组ID
            tag: 标签
            last_resource_x_id: 最新的资源ID
            
        Returns:
            操作是否成功
        """
        session = self.Session()
        try:
            subscription = session.query(TelegramSubscriptions).filter_by(
                chat_id=chat_id, tag=tag, is_active=True
            ).first()
            
            if subscription:
                from datetime import datetime
                subscription.last_resource_x_id = last_resource_x_id
                subscription.updated_at = datetime.now()
                session.commit()
                logger.info(f"✅ 更新订阅进度: chat_id={chat_id}, tag='{tag}', last_id={last_resource_x_id}")
                return True
                
            logger.warning(f"⚠️ 尝试更新不存在的订阅: chat_id={chat_id}, tag='{tag}'")
            return False
            
        except Exception as error:
            session.rollback()
            logger.error(f"❌ 更新订阅进度失败: {error}", exc_info=True)
            return False
        finally:
            session.close()

    def get_new_resources_for_subscription(self, subscription: TelegramSubscriptions) -> List[dict]:
        """
        获取订阅的新资源内容
        
        Args:
            subscription: 订阅对象
            
        Returns:
            新资源列表
        """
        session = self.Session()
        try:
            # 查询ResourceX表中比订阅进度更新的内容
            query = """
                SELECT id, fullText, images, videos, tags, publishTime 
                FROM resource.resource_x 
                WHERE id > :last_resource_id 
                AND (tags LIKE :tag_pattern OR fullText LIKE :tag_pattern)
                ORDER BY id ASC
                LIMIT 10
            """
            
            tag_pattern = f"%{subscription.tag}%"
            result = session.execute(
                query, 
                {
                    'last_resource_id': subscription.last_resource_x_id,
                    'tag_pattern': tag_pattern
                }
            ).fetchall()
            
            resources = []
            for row in result:
                resources.append({
                    'id': row[0],
                    'content': row[1],
                    'images': row[2],
                    'videos': row[3],
                    'tags': row[4],
                    'publish_time': row[5]
                })
            
            logger.info(f"📊 为订阅 {subscription.chat_id} 找到 {len(resources)} 个新资源")
            return resources
            
        except Exception as error:
            logger.error(f"❌ 查询新资源失败: {error}", exc_info=True)
            return []
        finally:
            session.close()

    def get_active_subscriptions(self) -> List[TelegramSubscriptions]:
        """
        获取所有活跃的订阅
        
        Returns:
            活跃订阅列表
        """
        session = self.Session()
        try:
            subscriptions = session.query(TelegramSubscriptions).filter_by(
                is_active=True
            ).all()
            logger.info(f"📋 找到 {len(subscriptions)} 个活跃订阅")
            return subscriptions
            
        except Exception as error:
            logger.error(f"❌ 获取活跃订阅失败: {error}", exc_info=True)
            return []
        finally:
            session.close()

    def save_telegram_setting(self, setting_type: str, config: Dict[str, Any]) -> Optional[TelegramSettings]:
        """
        保存Telegram设置到数据库
        
        Args:
            setting_type: 设置类型
            config: 配置内容
            
        Returns:
            保存的设置对象或None
        """
        session = self.Session()
        try:
            from datetime import datetime
            
            # 检查是否已存在相同类型的设置
            existing = session.query(TelegramSettings).filter_by(type=setting_type).first()
            
            if existing:
                # 更新现有设置
                existing.config = config
                existing.updated_at = datetime.now()
            else:
                # 创建新设置
                existing = TelegramSettings(
                    type=setting_type,
                    config=config,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                session.add(existing)
            
            session.commit()
            logger.info(f"✅ 成功保存Telegram设置: {setting_type}")
            return existing
            
        except Exception as error:
            session.rollback()
            logger.error(f"❌ 保存Telegram设置失败: {error}", exc_info=True)
            return None
        finally:
            session.close()