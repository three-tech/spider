import json
from base.logger import get_logger

logging = get_logger('database')
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class ResourceX(Base):
    """resource_x表模型"""
    __tablename__ = 'resource_x'
    __table_args__ = {'schema': 'resource'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    screenName = Column('screenName', String(45), nullable=False, comment='用户名')
    images = Column('images', Text, comment='图片链接列表')
    videos = Column('videos', Text, comment='视频链接列表')
    tweetUrl = Column('tweetUrl', String(255), nullable=False, unique=True, comment='推文链接')
    fullText = Column('fullText', String(255), comment='推文完整文本')
    publishTime = Column('publishTime', DateTime, comment='发布时间')
    create_time = Column('create_time', DateTime, nullable=False, default=datetime.now, comment='创建时间')
    update_time = Column('update_time', DateTime, nullable=False, default=datetime.now, onupdate=datetime.now,
                         comment='更新时间')


class MemberX(Base):
    """member_x表模型 - X平台会员信息缓存"""
    __tablename__ = 'member_x'
    __table_args__ = {'schema': 'resource'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column('user_id', BigInteger, unique=True, nullable=False, comment='用户ID')
    screen_name = Column('screen_name', String(255), nullable=False, comment='用户名')
    name = Column('name', String(255), nullable=True, comment='显示名称')
    description = Column('description', Text, nullable=True, comment='用户描述')
    followers_count = Column('followers_count', Integer, default=0, comment='粉丝数')
    friends_count = Column('friends_count', Integer, default=0, comment='关注数')
    statuses_count = Column('statuses_count', Integer, default=0, comment='推文数')
    profile_image_url = Column('profile_image_url', String(500), nullable=True, comment='头像URL')
    profile_banner_url = Column('profile_banner_url', String(500), nullable=True, comment='横幅URL')
    location = Column('location', String(255), nullable=True, comment='位置')
    verified = Column('verified', Integer, default=0, comment='是否认证 0-否 1-是')
    protected = Column('protected', Integer, default=0, comment='是否保护 0-否 1-是')
    follow = Column('follow', Integer, default=0, comment='是否关注 0-否 1-是')
    process_retweets = Column('process_retweets', Integer, default=0, comment='是否处理转发推文 0-否 1-是')
    filter_quotes = Column('filter_quotes', Integer, default=1, comment='是否过滤引用推文 0-否 1-是')
    last_crawl_time = Column('last_crawl_time', DateTime, nullable=True, comment='最后爬取时间')
    last_tweet_time = Column('last_tweet_time', DateTime, nullable=True, comment='最新推文时间')
    account_created_at = Column('account_created_at', String(255), nullable=True, comment='账户创建时间')
    tags = Column('tags', Text, comment='标签列表，逗号分隔')
    raw_data = Column('raw_data', Text, nullable=True, comment='原始API数据JSON')
    create_time = Column('create_time', DateTime, nullable=False, default=datetime.now, comment='创建时间')
    update_time = Column('update_time', DateTime, nullable=False, default=datetime.now, onupdate=datetime.now,
                         comment='更新时间')


class MemberXhs(Base):
    """member_xhs表模型 - 小红书会员信息"""
    __tablename__ = 'member_xhs'
    __table_args__ = {'schema': 'resource'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    userName = Column('userName', String(255), nullable=False, comment='用户名')
    tags = Column('tags', Text, comment='标签列表，逗号分隔')
    topic = Column('topic', String(500), nullable=True, comment='主题描述')
    xhs_id = Column('xhs_id', String(255), unique=True, nullable=False, comment='小红书用户ID')
    last_published_tweet_id = Column('last_published_tweet_id', Integer, nullable=True, comment='上次发布的推文ID')
    last_published_time = Column('last_published_time', DateTime, nullable=True, comment='上次发布的推文时间')
    create_time = Column('create_time', DateTime, nullable=False, default=datetime.now, comment='创建时间')
    update_time = Column('update_time', DateTime, nullable=False, default=datetime.now, onupdate=datetime.now,
                         comment='更新时间')


class DatabaseManager:
    def __init__(self, config=None, host='localhost', port=3306, user='root', password='123456', database='resource'):
        """初始化数据库管理器"""
        if config and isinstance(config, dict):
            # 如果传入配置字典，使用字典中的值
            self.host = config.get('host', host)
            self.port = config.get('port', port)
            self.user = config.get('user', user)
            self.password = config.get('password', password)
            self.database = config.get('database', database)
        else:
            # 否则使用传入的参数
            self.host = host
            self.port = port
            self.user = user
            self.password = password
            self.database = database

        self.engine = None
        self.Session = None

        self.setup_database()

    def setup_database(self):
        """设置数据库连接"""
        try:
            # 创建数据库连接
            connection_string = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?charset=utf8mb4"
            self.engine = create_engine(
                connection_string,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600
            )

            # 创建会话
            self.Session = sessionmaker(bind=self.engine)

            logging.info("数据库连接成功")

        except Exception as e:
            logging.error(f"数据库连接失败: {e}")
            raise

    def save_tweet(self, tweet_data):
        """保存单条推文数据"""
        session = self.Session()
        try:
            # 检查推文是否已存在
            existing_tweet = session.query(ResourceX).filter_by(tweetUrl=tweet_data.get('tweetUrl')).first()

            if existing_tweet:
                logging.info(f"推文已存在，跳过: {tweet_data.get('tweetUrl')}")
                return False

            # 处理发布时间
            publish_time = None
            if tweet_data.get('publishTime'):
                try:
                    if isinstance(tweet_data['publishTime'], str):
                        # 尝试解析ISO格式时间
                        publish_time = datetime.fromisoformat(tweet_data['publishTime'].replace('Z', '+00:00'))
                    elif isinstance(tweet_data['publishTime'], datetime):
                        publish_time = tweet_data['publishTime']
                except Exception as e:
                    logging.warning(f"解析发布时间失败: {e}")

            # 创建新记录
            new_tweet = ResourceX(
                screenName=tweet_data.get('screenName', ''),
                images=tweet_data.get('images', ''),
                videos=tweet_data.get('videos', ''),
                tweetUrl=tweet_data.get('tweetUrl', ''),
                fullText=tweet_data.get('fullText', ''),
                publishTime=publish_time
            )

            session.add(new_tweet)
            session.commit()

            logging.info(f"推文保存成功: {tweet_data.get('tweetUrl')}")
            return True

        except Exception as e:
            session.rollback()
            logging.error(f"保存推文失败: {e}")
            return False
        finally:
            session.close()

    def search_members_by_tag(self, tag):
        """根据标签搜索X平台会员"""
        session = self.Session()
        try:
            # 在member_x表中搜索包含指定标签的用户
            members = session.query(MemberX).filter(
                MemberX.tags.like(f'%{tag}%')
            ).all()

            return members

        except Exception as e:
            logging.error(f"根据标签搜索会员失败: {e}")
            return []
        finally:
            session.close()

    def get_unpublished_tweet_by_xhs_member(self, xhs_id, matching_screen_names):
        """
        根据小红书会员ID和匹配的X用户列表获取未发布推文
        
        Args:
            xhs_id: 小红书用户ID
            matching_screen_names: 匹配的X用户名列表
            
        Returns:
            dict: 未发布的推文信息，如果没有则返回None
        """
        session = self.Session()
        try:
            # 获取小红书会员的上次发布推文时间
            xhs_member = session.query(MemberXhs).filter_by(xhs_id=xhs_id).first()
            last_published_time = None
            if xhs_member and xhs_member.last_published_time:
                last_published_time = xhs_member.last_published_time

            # 查找匹配用户中发布时间大于已发布时间的推文
            query = session.query(ResourceX).filter(
                ResourceX.screenName.in_(matching_screen_names)  # 在匹配的用户列表中
            )
            
            if last_published_time:
                # 如果有上次发布时间，查找发布时间大于该时间的推文
                query = query.filter(ResourceX.publishTime > last_published_time)
            
            # 按发布时间升序获取最早的未发布推文
            tweet = query.order_by(ResourceX.publishTime.asc()).first()

            return tweet

        except Exception as e:
            logging.error(f"获取未发布推文失败: {e}")
            return None
        finally:
            session.close()

    def mark_tweet_as_published(self, tweet_id, xhs_id):
        """
        标记推文为已发布，并更新小红书会员的最后发布推文ID
        
        Args:
            tweet_id: 推文ID
            xhs_id: 小红书用户ID
            
        Returns:
            bool: 是否成功
        """
        session = self.Session()
        try:
            # 更新推文的更新时间作为发布标记
            tweet = session.query(ResourceX).filter(ResourceX.id == tweet_id).first()
            if not tweet:
                logging.warning(f"未找到推文 {tweet_id}")
                return False

            tweet.update_time = datetime.now()

            # 更新小红书会员的最后发布推文时间和ID
            xhs_member = session.query(MemberXhs).filter_by(xhs_id=xhs_id).first()
            if xhs_member:
                xhs_member.last_published_tweet_id = tweet_id
                xhs_member.last_published_time = tweet.publishTime
                xhs_member.update_time = datetime.now()
                logging.info(f"更新小红书会员 {xhs_id} 的最后发布推文时间为 {tweet.publishTime}")
            else:
                logging.warning(f"未找到小红书会员 {xhs_id}")

            session.commit()
            logging.info(f"推文 {tweet_id} 已标记为已发布")
            return True

        except Exception as e:
            session.rollback()
            logging.error(f"标记推文为已发布失败: {e}")
            return False
        finally:
            session.close()

    def save_tweets_batch(self, tweets_list):
        """批量保存推文数据"""
        session = self.Session()
        success_count = 0

        try:
            for tweet_data in tweets_list:
                try:
                    # 检查推文是否已存在
                    existing_tweet = session.query(ResourceX).filter_by(tweetUrl=tweet_data.get('tweetUrl')).first()

                    if existing_tweet:
                        # 更新已存在推文的媒体信息
                        images_str = ','.join(tweet_data.get('images', [])) if tweet_data.get('images') else None
                        videos_str = ','.join(tweet_data.get('videos', [])) if tweet_data.get('videos') else None

                        # 只有当媒体信息不同时才更新
                        if existing_tweet.images != images_str or existing_tweet.videos != videos_str:
                            existing_tweet.images = images_str
                            existing_tweet.videos = videos_str
                            existing_tweet.update_time = datetime.now()
                            logging.info(f"更新推文媒体信息: {tweet_data.get('tweetUrl')}")
                            success_count += 1
                        else:
                            logging.info(f"推文媒体信息无变化，跳过: {tweet_data.get('tweetUrl')}")
                        continue

                    # 处理发布时间
                    publish_time = None
                    if tweet_data.get('publishTime'):
                        try:
                            if isinstance(tweet_data['publishTime'], str):
                                publish_time = datetime.fromisoformat(tweet_data['publishTime'].replace('Z', '+00:00'))
                            elif isinstance(tweet_data['publishTime'], datetime):
                                publish_time = tweet_data['publishTime']
                        except Exception as e:
                            logging.warning(f"解析发布时间失败: {e}")

                    # 创建新记录
                    new_tweet = ResourceX(
                        screenName=tweet_data.get('screenName', ''),
                        images=','.join(tweet_data.get('images', [])) if tweet_data.get('images') else None,
                        videos=','.join(tweet_data.get('videos', [])) if tweet_data.get('videos') else None,
                        tweetUrl=tweet_data.get('tweetUrl', ''),
                        fullText=tweet_data.get('fullText', ''),
                        publishTime=publish_time
                    )

                    session.add(new_tweet)
                    success_count += 1

                except Exception as e:
                    logging.error(f"处理推文数据失败: {e}")
                    continue

            # 提交所有更改
            session.commit()
            logging.info(f"批量保存完成，成功保存 {success_count} 条推文")

        except Exception as e:
            session.rollback()
            logging.error(f"批量保存推文失败: {e}")
        finally:
            session.close()

        return success_count

    def get_tweet_count(self):
        """获取推文总数"""
        session = self.Session()
        try:
            count = session.query(ResourceX).count()
            return count
        except Exception as e:
            logging.error(f"获取推文数量失败: {e}")
            return 0
        finally:
            session.close()

    def get_tweets_by_user(self, screen_name, limit=10):
        """根据用户名获取推文"""
        session = self.Session()
        try:
            tweets = session.query(ResourceX).filter_by(screenName=screen_name).limit(limit).all()
            return tweets
        except Exception as e:
            logging.error(f"获取用户推文失败: {e}")
            return []
        finally:
            session.close()

    def get_member_by_screen_name(self, screen_name):
        """根据用户名获取会员信息"""
        session = self.Session()
        try:
            member = session.query(MemberX).filter_by(screen_name=screen_name).first()
            if member:
                logging.info(f"从本地缓存获取到会员信息: @{screen_name}")
                return member
            else:
                logging.info(f"本地缓存中未找到会员信息: @{screen_name}")
                return None
        except Exception as e:
            logging.error(f"获取会员信息失败: {e}")
            return None
        finally:
            session.close()

    def get_member_by_user_id(self, user_id):
        """根据用户ID获取会员信息"""
        session = self.Session()
        try:
            member = session.query(MemberX).filter_by(user_id=int(user_id)).first()
            if member:
                logging.info(f"从本地缓存获取到会员信息: ID={user_id}")
                return member
            else:
                logging.info(f"本地缓存中未找到会员信息: ID={user_id}")
                return None
        except Exception as e:
            logging.error(f"获取会员信息失败: {e}")
            return None
        finally:
            session.close()

    def save_member(self, user_data, follow=False):
        """保存会员信息到本地缓存"""
        session = self.Session()
        try:
            user_id = int(user_data.get('id_str', 0))
            screen_name = user_data.get('screen_name', '')

            if not user_id or not screen_name:
                logging.warning("用户ID或用户名为空，跳过保存")
                return False

            # 检查是否已存在
            existing_member = session.query(MemberX).filter_by(user_id=user_id).first()

            if existing_member:
                # 更新现有记录
                existing_member.screen_name = screen_name
                existing_member.name = user_data.get('name', '')
                existing_member.description = user_data.get('description', '')
                existing_member.followers_count = user_data.get('followers_count', 0)
                existing_member.friends_count = user_data.get('friends_count', 0)
                existing_member.statuses_count = user_data.get('statuses_count', 0)
                existing_member.profile_image_url = user_data.get('profile_image_url_https', '')
                existing_member.profile_banner_url = user_data.get('profile_banner_url', '')
                existing_member.location = user_data.get('location', '')
                existing_member.verified = 1 if user_data.get('verified', False) else 0
                existing_member.protected = 1 if user_data.get('protected', False) else 0
                # 如果传入了follow参数，则更新follow状态
                if follow is not None:
                    existing_member.follow = 1 if follow else 0
                existing_member.account_created_at = user_data.get('created_at', '')
                # 处理tags字段
                if user_data.get('tags'):
                    existing_member.tags = ','.join(user_data.get('tags', [])) if isinstance(user_data.get('tags'),
                                                                                             list) else user_data.get(
                        'tags')
                existing_member.raw_data = json.dumps(user_data, ensure_ascii=False)
                existing_member.update_time = datetime.now()

                logging.info(f"更新会员信息: @{screen_name} (ID: {user_id}) follow={follow}")
            else:
                # 创建新记录
                new_member = MemberX(
                    user_id=user_id,
                    screen_name=screen_name,
                    name=user_data.get('name', ''),
                    description=user_data.get('description', ''),
                    followers_count=user_data.get('followers_count', 0),
                    friends_count=user_data.get('friends_count', 0),
                    statuses_count=user_data.get('statuses_count', 0),
                    profile_image_url=user_data.get('profile_image_url_https', ''),
                    profile_banner_url=user_data.get('profile_banner_url', ''),
                    location=user_data.get('location', ''),
                    verified=1 if user_data.get('verified', False) else 0,
                    protected=1 if user_data.get('protected', False) else 0,
                    follow=1 if follow else 0,
                    account_created_at=user_data.get('created_at', ''),
                    tags=','.join(user_data.get('tags', [])) if user_data.get('tags') and isinstance(
                        user_data.get('tags'), list) else user_data.get('tags'),
                    raw_data=json.dumps(user_data, ensure_ascii=False)
                )

                session.add(new_member)
                logging.info(f"保存新会员信息: @{screen_name} (ID: {user_id}) follow={follow}")

            session.commit()
            return True

        except Exception as e:
            session.rollback()
            logging.error(f"保存会员信息失败: {e}")
            return False
        finally:
            session.close()

    def get_followed_users(self):
        """获取所有关注的用户列表"""
        session = self.Session()
        try:
            followed_members = session.query(MemberX).filter_by(follow=1).all()
            users = []
            for member in followed_members:
                users.append({
                    'screen_name': member.screen_name,
                    'user_id': str(member.user_id),
                    'name': member.name,
                    'followers_count': member.followers_count,
                    'statuses_count': member.statuses_count,
                    'filter_quotes': member.filter_quotes,
                    'process_retweets': member.process_retweets
                })
            logging.info(f"获取到 {len(users)} 个关注的用户")
            return users
        except Exception as e:
            logging.error(f"获取关注用户列表失败: {e}")
            return []
        finally:
            session.close()

    def set_user_follow_status(self, screen_name, follow=True):
        """设置用户关注状态"""
        session = self.Session()
        try:
            member = session.query(MemberX).filter_by(screen_name=screen_name).first()
            if member:
                member.follow = 1 if follow else 0
                member.update_time = datetime.now()
                session.commit()
                logging.info(f"设置用户 @{screen_name} 关注状态为: {follow}")
                return True
            else:
                logging.warning(f"用户 @{screen_name} 不存在于member_x表中")
                return False
        except Exception as e:
            session.rollback()
            logging.error(f"设置用户关注状态失败: {e}")
            return False
        finally:
            session.close()

    def get_member_count(self):
        """获取会员总数"""
        session = self.Session()
        try:
            count = session.query(MemberX).count()
            return count
        except Exception as e:
            logging.error(f"获取会员数量失败: {e}")
            return 0
        finally:
            session.close()

    def get_user_last_crawl_info(self, screen_name):
        """获取用户最后爬取信息"""
        session = self.Session()
        try:
            member = session.query(MemberX).filter_by(screen_name=screen_name).first()
            if member:
                # 转换为字典格式返回
                return {
                    'id': member.id,
                    'user_id': member.user_id,
                    'screen_name': member.screen_name,
                    'name': member.name,
                    'description': member.description,
                    'followers_count': member.followers_count,
                    'friends_count': member.friends_count,
                    'statuses_count': member.statuses_count,
                    'verified': member.verified,
                    'protected': member.protected,
                    'profile_image_url': member.profile_image_url,
                    'profile_banner_url': member.profile_banner_url,
                    'location': member.location,
                    'account_created_at': member.account_created_at,
                    'tags': member.tags,
                    'follow': member.follow,
                    'process_retweets': member.process_retweets,
                    'filter_quotes': member.filter_quotes,
                    'last_crawl_time': member.last_crawl_time,
                    'last_tweet_time': member.last_tweet_time,
                    'create_time': member.create_time,
                    'update_time': member.update_time,
                    'raw_data': member.raw_data
                }
            return None
        except Exception as e:
            logging.error(f"获取用户爬取信息失败: {e}")
            return None
        finally:
            session.close()

    def update_user_crawl_info(self, screen_name, last_tweet_time=None):
        """更新用户爬取信息"""
        session = self.Session()
        try:
            member = session.query(MemberX).filter_by(screen_name=screen_name).first()
            if member:
                member.last_crawl_time = datetime.now()
                if last_tweet_time:
                    member.last_tweet_time = last_tweet_time
                session.commit()
                logging.info(f"✅ 更新用户 @{screen_name} 爬取信息成功")
                return True
            else:
                logging.warning(f"⚠️ 用户 @{screen_name} 不存在于member_x表中")
                return False
        except Exception as e:
            logging.error(f"❌ 更新用户爬取信息失败: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def get_latest_tweet_time_by_user(self, screen_name):
        """获取用户在数据库中最新的推文时间"""
        session = self.Session()
        try:
            latest_tweet = session.query(ResourceX).filter_by(screenName=screen_name).order_by(
                ResourceX.publishTime.desc()).first()
            if latest_tweet and latest_tweet.publishTime:
                return latest_tweet.publishTime
            return None
        except Exception as e:
            logging.error(f"获取用户最新推文时间失败: {e}")
            return None
        finally:
            session.close()

    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            logging.info("数据库连接已关闭")

    # ==================== MemberXhs 相关方法 ====================

    def save_member_xhs(self, member_data):
        """保存小红书会员信息"""
        session = self.Session()
        try:
            # 检查是否已存在
            existing_member = session.query(MemberXhs).filter_by(xhs_id=member_data['xhs_id']).first()

            if existing_member:
                # 更新现有记录
                existing_member.userName = member_data.get('userName', existing_member.userName)
                existing_member.tags = member_data.get('tags', existing_member.tags)
                existing_member.update_time = datetime.now()
                session.commit()
                logging.info(f"✅ 更新小红书会员信息: {member_data['userName']}")
                return False  # 表示是更新，不是新增
            else:
                # 创建新记录
                new_member = MemberXhs(
                    userName=member_data['userName'],
                    tags=member_data.get('tags', ''),
                    xhs_id=member_data['xhs_id']
                )
                session.add(new_member)
                session.commit()
                logging.info(f"✅ 保存新的小红书会员信息: {member_data['userName']}")
                return True  # 表示是新增

        except Exception as e:
            logging.error(f"❌ 保存小红书会员信息失败: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def get_member_xhs_by_id(self, xhs_id):
        """根据小红书ID获取会员信息"""
        session = self.Session()
        try:
            member = session.query(MemberXhs).filter_by(xhs_id=xhs_id).first()
            return member
        except Exception as e:
            logging.error(f"❌ 获取小红书会员信息失败: {e}")
            return None
        finally:
            session.close()

    def get_all_member_xhs(self):
        """获取所有小红书会员信息"""
        session = self.Session()
        try:
            members = session.query(MemberXhs).all()
            return members
        except Exception as e:
            logging.error(f"❌ 获取所有小红书会员信息失败: {e}")
            return []
        finally:
            session.close()

    def update_member_xhs_tags(self, xhs_id, tags):
        """更新小红书会员标签"""
        session = self.Session()
        try:
            member = session.query(MemberXhs).filter_by(xhs_id=xhs_id).first()
            if member:
                member.tags = tags
                member.update_time = datetime.now()
                session.commit()
                logging.info(f"✅ 更新小红书会员标签: {member.userName}")
                return True
            else:
                logging.warning(f"⚠️ 小红书会员不存在: {xhs_id}")
                return False
        except Exception as e:
            logging.error(f"❌ 更新小红书会员标签失败: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def delete_member_xhs(self, xhs_id):
        """删除小红书会员信息"""
        session = self.Session()
        try:
            member = session.query(MemberXhs).filter_by(xhs_id=xhs_id).first()
            if member:
                session.delete(member)
                session.commit()
                logging.info(f"✅ 删除小红书会员信息: {member.userName}")
                return True
            else:
                logging.warning(f"⚠️ 小红书会员不存在: {xhs_id}")
                return False
        except Exception as e:
            logging.error(f"❌ 删除小红书会员信息失败: {e}")
            session.rollback()
            return False
        finally:
            session.close()
