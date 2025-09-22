#!/usr/bin/env python3
"""
优化版X平台爬虫 - 基于twitter-openapi-typescript的Python实现
参考: /Users/xuzongxin/workspace/other/XT-Bot/TypeScript/scripts/fetch-tweets.ts
"""

import json
import time
import os
import re
import requests
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Generator
# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 现在导入base模块
from base.logger import get_logger
from base.database import DatabaseManager
try:
    from x_auth_client import create_x_auth_client, XAuthClient
except ImportError:
    from .x_auth_client import create_x_auth_client, XAuthClient

class XSpiderOptimized:
    def __init__(self, config_path="config.json"):
        """初始化优化版X平台爬虫"""
        self.config = self.load_config(config_path)
        self.db_manager = None
        self.twitter_client = None
        self.setup_logging()
        self.setup_database()
        self.setup_twitter_client()
        
    def load_config(self, config_path):
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"配置文件 {config_path} 不存在")
            raise
        except json.JSONDecodeError:
            self.logger.error(f"配置文件 {config_path} 格式错误")
            raise
    
    def setup_logging(self):
        """设置日志 - 使用统一的loguru日志系统"""
        from base.logger import get_logger
        self.logger = get_logger(self.__class__.__name__)
        return self.logger
    
    def setup_database(self):
        """设置数据库连接"""
        try:
            db_config = self.config.get("database", {})
            self.db_manager = DatabaseManager(
                host=db_config.get("host", "localhost"),
                port=db_config.get("port", 3306),
                user=db_config.get("user", "root"),
                password=db_config.get("password", "123456"),
                database=db_config.get("database", "resource")
            )
            self.logger.info("数据库连接初始化成功")
        except Exception as e:
            self.logger.error(f"数据库连接初始化失败: {e}")
            self.db_manager = None
            # 不抛出异常，允许程序继续运行但无法使用数据库功能
    
    def setup_twitter_client(self):
        """设置X认证客户端"""
        try:
            api_config = self.config.get("api", {})
            auth_token = api_config.get("auth_token", "")
            
            if not auth_token:
                self.logger.error("❌ 未配置auth_token，无法初始化X客户端")
                self.twitter_client = None
                return
            
            self.twitter_client = create_x_auth_client(auth_token)
            self.logger.info("✅ X认证客户端初始化成功")
            
        except Exception as e:
            self.logger.error(f"❌ X认证客户端初始化失败: {e}")
            self.twitter_client = None
    
    def get_user_info(self, screen_name: str, force_refresh: bool = False) -> Optional[Dict[str, str]]:
        """获取用户信息 - 优先从member_x表获取，然后是文件缓存，最后调用API"""
        try:
            # 步骤1: 优先从数据库member_x表获取
            if not force_refresh and self.db_manager:
                cached_user = self.db_manager.get_member_by_screen_name(screen_name)
                if cached_user:
                    self.logger.info(f"📦 从数据库缓存获取用户信息：@{screen_name}")
                    return {
                        "screenName": cached_user.screen_name,
                        "userId": str(cached_user.user_id),
                        "name": cached_user.name
                    }
            
            # 步骤2: 尝试读取文件缓存
            cache_dir = "../resp/cache"
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, f"{screen_name}.json")
            
            if not force_refresh and os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cached = json.load(f)
                    if cached.get('userId'):
                        self.logger.info(f"📦 使用文件缓存用户信息：@{screen_name}")
                        return cached
                except Exception as e:
                    logging.warning(f"读取文件缓存失败: {e}")
            
            # 步骤3: 调用API获取新数据
            self.logger.info(f"🌐 正在请求API获取用户信息：@{screen_name}")
            
            # 构建API请求
            user_info = self._fetch_user_by_screen_name(screen_name)
            
            if not user_info:
                raise Exception(f"未找到用户 @{screen_name}")
            
            # 步骤4: 保存到数据库缓存
            try:
                # 获取完整的用户数据用于保存到数据库
                full_user_data = self.twitter_client.get_user_by_screen_name(screen_name)
                if full_user_data and self.db_manager:
                    save_success = self.db_manager.save_member(full_user_data)
                    if save_success:
                        self.logger.info(f"✅ 用户信息已保存到数据库缓存：@{screen_name}")
                    else:
                        self.logger.warning(f"⚠️ 用户信息保存到数据库失败：@{screen_name}")
            except Exception as e:
                self.logger.warning(f"保存用户信息到数据库时出错: {e}")
            
            # 步骤5: 写入文件缓存
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(user_info, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 获取用户信息成功: @{user_info['screenName']} (ID: {user_info['userId']})")
            return user_info
            
        except Exception as e:
            self.logger.error(f"获取用户信息失败: {e}")
            return None
    
    def _fetch_user_by_screen_name(self, screen_name: str) -> Optional[Dict[str, str]]:
        """通过用户名获取用户信息 - 使用X认证客户端"""
        try:
            if not self.twitter_client:
                self.logger.error("X认证客户端未初始化")
                return None
            
            # 使用X认证客户端获取用户信息
            user_data = self.twitter_client.get_user_by_screen_name(screen_name)
            
            if user_data and user_data.get('id_str'):
                return {
                    "screenName": user_data.get('screen_name', screen_name),
                    "userId": user_data.get('id_str', ''),
                    "name": user_data.get('name', screen_name)
                }
            else:
                self.logger.error(f"未找到用户 @{screen_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"获取用户信息异常: {e}")
            return None
    
    def transform_tweet(self, item: Dict[str, Any], user_id: str, filter_retweets: bool = True, filter_quotes: bool = True) -> Optional[Dict[str, Any]]:
        """转换推文数据 - 参考TypeScript版本的transformTweet函数"""
        try:
            # 调试：打印推文数据结构的关键部分
            logging.debug(f"推文数据键: {list(item.keys())}")
            if isinstance(item, dict) and 'legacy' in item:
                logging.debug(f"legacy键: {list(item['legacy'].keys())}")
            # 安全获取字段值
            def safe_get(path: str, default_value: Any = '') -> Any:
                keys = path.split('.')
                value = item
                for key in keys:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        return default_value
                return value
            
            # 提取推文内容 - 修复字段名
            full_text = safe_get('legacy.full_text', '')
            
            # 过滤转推
            if filter_retweets and full_text.strip().startswith("RT @"):
                return None
            
            # 过滤引用推文
            is_quote_status = safe_get('legacy.is_quote_status', False)
            if filter_quotes and is_quote_status:
                return None
            
            # 处理发布时间 - 修复时间字段获取
            created_at = safe_get('legacy.created_at', '')
            publish_time = self.convert_to_beijing_time(created_at)
            if not publish_time:
                logging.warning(f"🕒 时间解析失败: {created_at}")
                # 不返回None，使用当前时间作为备选
                publish_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            
            # 用户信息 - 修复字段名
            user = {
                "screenName": safe_get('core.user_results.result.legacy.screen_name', ''),
                "name": safe_get('core.user_results.result.legacy.name', '')
            }
            
            # 多媒体内容处理 - 修复字段名
            media_items = safe_get('legacy.extended_entities.media', [])
            
            # 如果扩展媒体实体为空，尝试基础媒体实体
            if not media_items:
                media_items = safe_get('legacy.entities.media', [])
            
            # 图片提取 - 修复字段名
            images = []
            for media in media_items:
                if media.get('type') == 'photo':
                    # 修复字段名：media_url_https 而不是 mediaUrlHttps
                    media_url = media.get('media_url_https')
                    if media_url:
                        images.append(media_url)
                        logging.debug(f"📸 提取图片: {media_url}")
            
            # 视频提取 - 修复字段名
            videos = []
            for media in media_items:
                if media.get('type') in ['video', 'animated_gif']:
                    # 修复字段名：video_info 而不是 videoInfo
                    video_info = media.get('video_info', {})
                    variants = video_info.get('variants', [])
                    # 选择最高质量的mp4视频 - 修复字段名
                    mp4_variants = [v for v in variants if v.get('content_type') == 'video/mp4']
                    if mp4_variants:
                        best_variant = max(mp4_variants, key=lambda x: x.get('bitrate', 0))
                        videos.append(best_variant['url'])
                        logging.debug(f"🎬 提取视频: {best_variant['url'][:50]}...")
            
            # 链接处理
            expand_urls = []
            urls = safe_get('legacy.entities.urls', [])
            for url in urls:
                expanded_url = url.get('expandedUrl')
                if expanded_url:
                    expand_urls.append(expanded_url)
            
            # 构造推文URL - 修复字段名
            tweet_id = safe_get('legacy.id_str', '') or safe_get('rest_id', '')
            if not tweet_id or not user['screenName']:
                # 调试信息：打印数据结构
                logging.warning(f"❌ 无效推文结构 - tweet_id: {tweet_id}, screenName: {user['screenName']}")
                return None
            
            tweet_url = f"https://x.com/{user['screenName']}/status/{tweet_id}"
            
            logging.info(f"✅ 转换成功: {tweet_url}")
            
            return {
                "screenName": user['screenName'],
                "images": images,
                "videos": videos,
                "tweetUrl": tweet_url,
                "fullText": full_text,
                "publishTime": publish_time
            }
            
        except Exception as e:
            logging.error(f"转换推文数据失败: {e}")
            return None
    
    def convert_to_beijing_time(self, date_str: str) -> Optional[str]:
        """转换到北京时间"""
        try:
            if not date_str:
                return None
            
            # 尝试解析Twitter时间格式
            # 例: "Wed Oct 10 20:19:24 +0000 2018"
            dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
            
            # 转换为北京时间 (UTC+8)
            from datetime import timedelta
            beijing_tz = timezone(timedelta(hours=8))
            beijing_time = dt.astimezone(beijing_tz)
            
            return beijing_time.strftime('%Y-%m-%dT%H:%M:%S')
            
        except Exception as e:
            logging.warning(f"时间转换失败: {e}")
            # 返回当前时间作为备选
            return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    
    def tweet_cursor_generator(self, user_id: str, limit: int = 50, content_type: str = 'tweets') -> Generator[Dict[str, Any], None, None]:
        """分页生成器 - 模拟API分页请求"""
        cursor = None
        count = 0
        empty_count = 0
        page_count = 0
        
        while count < limit:
            page_count += 1
            logging.info(f"\n=== 第 {page_count} 次请求 ===")
            logging.info(f"⏱️ 请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logging.info(f"🎯 目标用户ID: {user_id}")
            
            if cursor:
                logging.info(f"📍 当前游标: {cursor}")
            
            # 请求间隔
            if page_count > 1:
                interval = self.config.get("delay_between_requests", 2)
                logging.info(f"⏸️ 等待 {interval} 秒...")
                time.sleep(interval)
            
            # 真实API请求
            try:
                response_data = self.api_request_tweets(user_id, cursor, content_type)
                tweets = response_data.get('data', [])
                new_cursor = response_data.get('cursor')
                
                logging.info(f"🔄 获取到 {len(tweets)} 条推文")
                
                if len(tweets) == 0:
                    empty_count += 1
                    logging.info(f"❌ 空数据计数: {empty_count}/3")
                    if empty_count >= 3:
                        logging.info("⏹️ 终止原因：连续3次空响应")
                        break
                else:
                    empty_count = 0
                
                # 处理数据
                for item in tweets:
                    yield item
                    count += 1
                    if count >= limit:
                        logging.info(f"⏹️ 终止原因：达到数量限制（{limit}）")
                        return
                
                cursor = new_cursor
                if not cursor:
                    logging.info("⏹️ 终止原因：无更多数据")
                    break
                    
            except Exception as e:
                logging.error(f"API请求失败: {e}")
                break
        
        logging.info(f"📌 累计已处理: {count} 条")
    
    def api_request_tweets(self, user_id: str, cursor: Optional[str], content_type: str) -> Dict[str, Any]:
        """真实的API请求 - 获取用户推文"""
        try:
            if not self.twitter_client:
                logging.error("X认证客户端未初始化")
                return {"data": [], "cursor": None}
            
            # 使用X认证客户端获取推文
            response = self.twitter_client.get_user_tweets(user_id, cursor, count=20)
            
            if response:
                return response
            else:
                logging.warning("API返回空响应")
                return {"data": [], "cursor": None}
            
        except Exception as e:
            logging.error(f"API请求失败: {e}")
            return {"data": [], "cursor": None}
    

    
    def process_user_tweets(self, screen_name: str) -> List[Dict[str, Any]]:
        """处理用户推文的主流程 - 支持增量爬取"""
        start_time = time.time()
        logging.info("=" * 60)
        logging.info(f"🚀 开始处理用户 @{screen_name}")
        
        try:
            # 步骤1: 获取用户信息
            force_refresh = self.config.get("force_refresh", False)
            user_info = self.get_user_info(screen_name, force_refresh)
            if not user_info:
                logging.error(f"无法获取用户 @{screen_name} 的信息")
                return []
            
            # 步骤2: 检查增量爬取条件
            last_tweet_time = None
            if self.db_manager:
                crawl_info = self.db_manager.get_user_last_crawl_info(screen_name)
                if crawl_info and 'last_tweet_time' in crawl_info:
                    last_tweet_time = crawl_info['last_tweet_time']
                    logging.info(f"📅 上次爬取的最新推文时间: {last_tweet_time}")
                    logging.info("🔄 启用增量爬取模式，只获取新推文")
                else:
                    logging.info("🆕 首次爬取该用户，获取所有推文")
            else:
                logging.info("🆕 数据库未初始化，获取所有推文")
            
            # 步骤3: 获取配置参数
            max_tweets = self.config.get("max_tweets_per_user", 50)
            filter_retweets = not self.config.get("include_retweets", False)
            filter_quotes = True  # 默认过滤引用推文
            content_type = "tweets"  # 或 "media"
            
            # 步骤4: 获取并处理推文
            logging.info("⏳ 开始获取推文数据...")
            all_tweets = []
            processed_count = 0
            new_tweets_count = 0
            latest_tweet_time = None
            
            for item in self.tweet_cursor_generator(user_info['userId'], max_tweets, content_type):
                # 转换推文数据
                tweet_data = self.transform_tweet(item, user_info['userId'], filter_retweets, filter_quotes)
                if tweet_data:
                    # 解析推文时间
                    tweet_time_str = tweet_data.get('publishTime', '')
                    if tweet_time_str:
                        try:
                            # 转换为datetime对象进行比较
                            tweet_time = datetime.strptime(tweet_time_str, '%Y-%m-%dT%H:%M:%S')
                            
                            # 记录最新推文时间
                            if not latest_tweet_time or tweet_time > latest_tweet_time:
                                latest_tweet_time = tweet_time
                            
                            # 增量爬取：如果推文时间早于或等于上次爬取时间，停止爬取
                            if last_tweet_time and tweet_time <= last_tweet_time:
                                logging.info(f"⏹️ 遇到已爬取的推文 ({tweet_time_str})，停止爬取")
                                break
                            else:
                                new_tweets_count += 1
                                
                        except ValueError as e:
                            logging.warning(f"⚠️ 推文时间解析失败: {tweet_time_str}, {e}")
                    
                    all_tweets.append(tweet_data)
                    processed_count += 1
            
            # 步骤5: 批量保存到数据库
            success_count = 0
            if all_tweets:
                success_count = self.save_tweets_to_database(all_tweets)
                logging.info(f"✅ 成功保存 {success_count} 条推文到数据库")
            
            # 步骤6: 更新用户爬取信息
            if self.db_manager:
                if latest_tweet_time:
                    self.db_manager.update_user_crawl_info(screen_name, latest_tweet_time)
                    logging.info(f"📝 更新用户最新推文时间: {latest_tweet_time}")
                else:
                    # 即使没有新推文，也更新爬取时间
                    self.db_manager.update_user_crawl_info(screen_name)
                    logging.info("📝 更新用户爬取时间")
            else:
                logging.warning("⚠️ 数据库未初始化，无法更新爬取信息")
            
            # 统计信息
            time_cost = (time.time() - start_time)
            logging.info(f"""
🎉 处理完成！
├── 用户：@{user_info['screenName']} (ID: {user_info['userId']})
├── 获取：{len(all_tweets)} 条有效推文
├── 新推文：{new_tweets_count} 条
├── 保存：{success_count} 条到数据库
├── 最新推文时间：{latest_tweet_time or '无'}
├── 耗时：{time_cost:.1f} 秒
            """)
            
            return all_tweets
            
        except Exception as e:
            logging.error(f"❌ 处理用户 @{screen_name} 失败: {e}")
            return []
    
    def save_tweets_to_database(self, tweets: List[Dict[str, Any]]) -> int:
        """批量保存推文到数据库"""
        if not tweets:
            logging.warning("⚠️ 没有新数据需要插入")
            return 0
        
        logging.info(f"📊 准备插入数据库的数据量: {len(tweets)} 条")
        
        try:
            if self.db_manager:
                success_count = self.db_manager.save_tweets_batch(tweets)
                
                # 同时保存JSON备份
                self.save_json_backup(tweets)
                
                return success_count
            else:
                logging.error("数据库管理器未初始化")
                return 0
            
        except Exception as e:
            logging.error(f"保存推文数据到数据库时出错: {e}")
            return 0
    
    def save_json_backup(self, tweets: List[Dict[str, Any]]):
        """保存JSON备份"""
        try:
            output_file = self.config.get("output_file", "data/x/tweets.json")
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # 读取现有数据
            existing_data = []
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            
            # 合并数据
            all_data = existing_data + tweets
            
            # 去重（基于tweetUrl）
            unique_tweets = {}
            for tweet in all_data:
                unique_tweets[tweet['tweetUrl']] = tweet
            
            # 保存数据
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(list(unique_tweets.values()), f, ensure_ascii=False, indent=2)
            
            logging.info(f"JSON备份已保存到 {output_file}")
            
        except Exception as e:
            logging.error(f"保存JSON备份失败: {e}")
    
    def get_users_to_crawl(self):
        """获取需要爬取的用户列表 - 优化配置逻辑"""
        try:
            # 1. 优先检查配置文件中的users，如果不为空则只爬取指定用户
            config_users = self.config.get("users", [])
            if config_users:
                self.logger.info(f"📄 配置文件中指定了 {len(config_users)} 个用户，只爬取指定用户")
                for user in config_users:
                    self.logger.info(f"   - @{user}")
                return config_users
            
            # 2. 如果配置文件为空，则从数据库获取关注的用户
            if self.db_manager:
                followed_users = self.db_manager.get_followed_users()
                
                if followed_users:
                    self.logger.info(f"📦 从数据库获取到 {len(followed_users)} 个关注用户")
                    user_list = [user['screen_name'] for user in followed_users]
                    
                    # 显示用户列表
                    for user in followed_users:
                        self.logger.info(f"   - @{user['screen_name']} (粉丝: {user['followers_count']}, 推文: {user['statuses_count']})")
                    
                    return user_list
            
            # 3. 都没有则返回空列表
            self.logger.warning("⚠️ 未找到任何需要爬取的用户")
            self.logger.info("💡 请在config.json中配置users或在member_x表中设置follow=1的用户")
            return []
            
        except Exception as e:
            self.logger.error(f"获取用户列表失败: {e}")
            # 降级到配置文件
            return self.config.get("users", [])

    def get_my_following_list(self):
        """获取我的完整关注列表 - 循环获取所有用户"""
        try:
            logging.info("🔍 正在获取完整关注列表...")
            
            # 调用X认证客户端获取完整关注列表
            result = self.twitter_client.get_my_following()
            
            if result and 'users' in result:
                users = result['users']
                logging.info(f"✅ 成功获取到 {len(users)} 个关注用户")
                
                # 转换用户数据格式
                formatted_users = []
                for user in users:
                    formatted_user = {
                        'id_str': user.get('id_str', ''),
                        'screen_name': user.get('screen_name', ''),
                        'name': user.get('name', ''),
                        'description': user.get('description', ''),
                        'followers_count': user.get('followers_count', 0),
                        'friends_count': user.get('friends_count', 0),
                        'statuses_count': user.get('statuses_count', 0),
                        'verified': user.get('verified', False),
                        'profile_image_url_https': user.get('profile_image_url_https', ''),
                        'profile_banner_url': user.get('profile_banner_url', ''),
                        'location': user.get('location', ''),
                        'url': user.get('url', ''),
                        'created_at': user.get('created_at', ''),
                        'protected': user.get('protected', False)
                    }
                    formatted_users.append(formatted_user)
                
                return {
                    'users': formatted_users,
                    'count': len(formatted_users)
                }
            else:
                logging.error("❌ 获取关注列表失败")
                return None
                
        except Exception as e:
            logging.error(f"获取关注列表时出错: {e}")
            return None

    def run(self):
        """运行爬虫主程序"""
        # 获取需要爬取的用户列表
        users = self.get_users_to_crawl()
        
        if not users:
            logging.error("❌ 没有找到需要爬取的用户，程序退出")
            return []
        
        self.logger.info(f"🚀 开始爬取 {len(users)} 个用户的推文")
        
        all_results = []
        
        try:
            for username in users:
                try:
                    # 处理单个用户
                    user_tweets = self.process_user_tweets(username)
                    all_results.extend(user_tweets)
                    
                except Exception as e:
                    logging.error(f"处理用户 {username} 时出错: {e}")
                    continue
            
            logging.info(f"🎉 全部完成！共处理 {len(all_results)} 条推文")
            
        finally:
            if self.db_manager:
                self.db_manager.close()
                logging.info("数据库连接已关闭")
        
        return all_results

    def add_user_to_member_x(self, screen_name: str, follow: bool = False) -> bool:
        """
        根据输入的screen_name自动插入到member_x表中
        
        Args:
            screen_name: 用户名
            follow: 是否关注，默认为False
            
        Returns:
            bool: 是否成功添加
        """
        try:
            logging.info(f"🔍 正在获取用户 @{screen_name} 的信息...")
            
            # 获取用户信息
            user_info = self.get_user_info(screen_name, force_refresh=True)
            if not user_info:
                logging.error(f"❌ 无法获取用户 @{screen_name} 的信息")
                return False
            
            # 使用完整的用户数据
            full_user_data = self.twitter_client.get_user_by_screen_name(screen_name)
            if not full_user_data:
                logging.error(f"❌ 无法获取用户 @{screen_name} 的完整数据")
                return False
            
            # 保存到member_x表
            success = self.db_manager.save_member(full_user_data, follow=follow)
            
            if success:
                status = "关注" if follow else "未关注"
                logging.info(f"✅ 成功添加用户 @{screen_name} 到member_x表，状态：{status}")
                return True
            else:
                logging.error(f"❌ 添加用户 @{screen_name} 到member_x表失败")
                return False
                
        except Exception as e:
            logging.error(f"添加用户 @{screen_name} 时出错: {e}")
            return False

    def sync_following_to_member_x(self) -> int:
        """
        根据current_user_screen_name获取关注列表并插入或修改member_x表
        所有关注用户的follow状态默认为true
        
        Returns:
            int: 成功处理的用户数量
        """
        try:
            logging.info("🔄 开始同步关注列表到member_x表...")
            
            # 获取完整关注列表
            following_result = self.get_my_following_list()
            
            if not following_result or 'users' not in following_result:
                logging.error("❌ 获取关注列表失败")
                return 0
            
            users = following_result['users']
            logging.info(f"📋 获取到 {len(users)} 个关注用户，开始同步到数据库...")
            
            success_count = 0
            
            for i, user in enumerate(users, 1):
                try:
                    # 保存用户信息到member_x表，follow=True
                    success = self.db_manager.save_member(user, follow=True)
                    
                    if success:
                        success_count += 1
                        logging.info(f"   [{i:3d}/{len(users)}] ✅ @{user['screen_name']} - 已同步")
                    else:
                        logging.warning(f"   [{i:3d}/{len(users)}] ⚠️ @{user['screen_name']} - 同步失败")
                        
                except Exception as e:
                    logging.error(f"   [{i:3d}/{len(users)}] ❌ @{user.get('screen_name', 'unknown')} - 错误: {e}")
            
            logging.info(f"🎉 同步完成！成功处理 {success_count}/{len(users)} 个用户")
            
            # 显示统计信息
            total_members = self.db_manager.get_member_count()
            followed_users = self.db_manager.get_followed_users()
            logging.info(f"📊 数据库统计 - 总用户: {total_members}, 关注用户: {len(followed_users)}")
            
            return success_count
            
        except Exception as e:
            logging.error(f"同步关注列表时出错: {e}")
            return 0

if __name__ == "__main__":
    spider = XSpiderOptimized()
    spider.run()