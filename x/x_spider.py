#!/usr/bin/env python3
"""
优化版X平台爬虫 - 基于twitter-openapi-typescript的Python实现
参考: /Users/xuzongxin/workspace/other/XT-Bot/TypeScript/scripts/fetch-tweets.ts
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Generator

from x.x_auth_client import create_x_auth_client

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 现在导入base模块
from base.database import DatabaseManager


class XSpider:
    def __init__(self):
        """初始化优化版X平台爬虫"""
        # 使用统一的配置管理器
        self.logger = None
        from base.config import config
        self.config = config
        self.db_manager = None
        self.twitter_client = None
        # 先设置日志
        self.setup_logging()
        self.setup_database()
        self.setup_twitter_client()

    def setup_logging(self):
        """设置日志 - 使用统一的结构化日志系统"""
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
            self.logger.info("数据库连接初始化成功", component="database")
        except Exception as e:
            self.logger.error("数据库连接初始化失败", error=str(e))
            self.db_manager = None
            # 不抛出异常，允许程序继续运行但无法使用数据库功能

    def setup_twitter_client(self):
        """设置X认证客户端"""
        try:
            # 从统一配置中获取X平台配置
            auth_token = self.config.get_x_config().get('auth_token')

            if not auth_token:
                self.logger.error("未配置auth_token，无法初始化X客户端", component="authentication")
                self.twitter_client = None
                return

            self.twitter_client = create_x_auth_client(auth_token)
            self.logger.info("X认证客户端初始化成功", component="authentication")

        except Exception as e:
            self.logger.error("X认证客户端初始化失败", error=str(e))
            self.twitter_client = None

    def get_user_info(self, screen_name: str, force_refresh: bool = False) -> Optional[Dict[str, str]]:
        """获取用户信息 - 优先从member_x表获取，然后是文件缓存，最后调用API"""
        try:
            # 步骤1: 优先从数据库member_x表获取
            if not force_refresh and self.db_manager:
                cached_user = self.db_manager.get_member_by_screen_name(screen_name)
                if cached_user:
                    self.logger.info("从数据库缓存获取用户信息", screen_name=screen_name)
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
                        self.logger.info("使用文件缓存用户信息", screen_name=screen_name)
                        return cached
                except Exception as e:
                    logging.warning(f"读取文件缓存失败: {e}")

            # 步骤3: 调用API获取新数据
            self.logger.info("正在请求API获取用户信息", screen_name=screen_name)

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
                        self.logger.info("用户信息已保存到数据库缓存", screen_name=screen_name)
                    else:
                        self.logger.warning("用户信息保存到数据库失败", screen_name=screen_name)
            except Exception as e:
                self.logger.warning("保存用户信息到数据库时出错", error=str(e))

            # 步骤5: 写入文件缓存
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(user_info, f, ensure_ascii=False, indent=2)

            self.logger.info("获取用户信息成功",
                             screen_name=user_info['screenName'],
                             user_id=user_info['userId'])
            return user_info

        except Exception as e:
            self.logger.error("获取用户信息失败", error=str(e))
            return None

    def _fetch_user_by_screen_name(self, screen_name: str) -> Optional[Dict[str, str]]:
        """通过用户名获取用户信息 - 使用X认证客户端"""
        try:
            if not self.twitter_client:
                self.logger.error("X认证客户端未初始化", component="authentication")
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
                self.logger.error("未找到用户", screen_name=screen_name)
                return None

        except Exception as e:
            self.logger.error("获取用户信息异常", error=str(e))
            return None

    def transform_tweet(self, item: Dict[str, Any], user_id: str, filter_retweets: bool = True,
                        filter_quotes: bool = True) -> Optional[Dict[str, Any]]:
        """转换推文数据 - 增强转发推文处理功能"""
        try:
            # 快速失败检查
            if not self._should_process_tweet(item, filter_retweets, filter_quotes):
                return None

            # 提取基础信息
            full_text = self._safe_get(item, 'legacy.full_text', '')
            publish_time = self._get_publish_time(item)
            user_info = self._extract_user_info(item)

            # 检查必要字段
            if not self._has_required_fields(user_info, full_text):
                return None

            # 提取媒体和URL
            media_data = self._extract_media_data(item)
            tweet_url = self._build_tweet_url(user_info, item)

            logging.info(f"✅ 转换成功: {tweet_url}")

            return {
                "screenName": user_info["screenName"],
                "images": media_data["images"],
                "videos": media_data["videos"],
                "tweetUrl": tweet_url,
                "fullText": full_text,
                "publishTime": publish_time
            }

        except Exception as e:
            logging.error(f"转换推文数据失败: {e}")
            return None

    def _is_valid_tweet_structure(self, item: Dict[str, Any]) -> bool:
        """检查推文数据结构是否有效"""
        if not isinstance(item, dict):
            return False

        logging.debug(f"推文数据键: {list(item.keys())}")
        if 'legacy' in item:
            logging.debug(f"legacy键: {list(item['legacy'].keys())}")

        return True

    def _should_process_tweet(self, item: Dict[str, Any], filter_retweets: bool, filter_quotes: bool) -> bool:
        """判断是否应该处理推文 - 快速失败策略"""
        # 检查数据结构
        if not self._is_valid_tweet_structure(item):
            return False

        full_text = self._safe_get(item, 'legacy.full_text', '')

        # 过滤转推
        if filter_retweets and full_text.strip().startswith("RT @"):
            return False

        # 过滤引用推文
        if filter_quotes and self._safe_get(item, 'legacy.is_quote_status', False):
            return False

        return True

    def _safe_get(self, obj: Dict[str, Any], path: str, default_value: Any = '') -> Any:
        """安全获取嵌套字典值"""
        keys = path.split('.')
        value = obj
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default_value
        return value

    def _get_publish_time(self, item: Dict[str, Any]) -> str:
        """获取发布时间"""
        created_at = self._safe_get(item, 'legacy.created_at', '')
        publish_time = self.convert_to_beijing_time(created_at)

        if not publish_time:
            logging.warning(f"🕒 时间解析失败: {created_at}")
            publish_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        return publish_time

    def _extract_user_info(self, item: Dict[str, Any]) -> Dict[str, str]:
        """提取用户信息"""
        return {
            "screenName": self._safe_get(item, 'core.user_results.result.legacy.screen_name', ''),
            "name": self._safe_get(item, 'core.user_results.result.legacy.name', '')
        }

    def _has_required_fields(self, user_info: Dict[str, str], full_text: str) -> bool:
        """检查必要字段是否存在"""
        if not user_info["screenName"] or not full_text:
            logging.warning(f"❌ 缺少必要字段 - screenName: {user_info['screenName']}, full_text: {bool(full_text)}")
            return False
        return True

    def _extract_media_data(self, item: Dict[str, Any]) -> Dict[str, List[str]]:
        """提取媒体数据"""
        media_items = self._extract_all_media_items(item)
        images = self._extract_images(media_items)
        videos = self._extract_videos(media_items)

        return {
            "images": images,
            "videos": videos
        }

    def _extract_all_media_items(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取所有媒体项目"""
        # 优先尝试扩展媒体实体
        media_items = self._safe_get(item, 'legacy.extended_entities.media', [])

        # 如果为空，尝试基础媒体实体
        if not media_items:
            media_items = self._safe_get(item, 'legacy.entities.media', [])

        # 如果是转发推文且需要处理转发媒体
        if self._should_extract_retweet_media(item):
            retweet_media = self._extract_retweet_media(item)
            if retweet_media:
                media_items = retweet_media
                logging.debug("🔄 从转发源推文提取媒体内容")

        return media_items

    def _should_extract_retweet_media(self, item: Dict[str, Any]) -> bool:
        """判断是否应该提取转发推文的媒体"""
        full_text = self._safe_get(item, 'legacy.full_text', '')
        is_retweet = full_text.strip().startswith("RT @")

        if not is_retweet or not self.db_manager:
            return False

        user_info = self._extract_user_info(item)
        db_user = self.db_manager.get_member_by_screen_name(user_info["screenName"])

        return db_user and db_user.process_retweets

    def _extract_retweet_media(self, item: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """从转发源推文提取媒体"""
        retweeted_status = self._safe_get(item, 'legacy.retweeted_status_result.result', {})
        if not retweeted_status:
            return None

        # 尝试扩展媒体实体
        retweet_media = self._safe_get(retweeted_status, 'legacy.extended_entities.media', [])
        if not retweet_media:
            retweet_media = self._safe_get(retweeted_status, 'legacy.entities.media', [])

        return retweet_media if retweet_media else None

    def _extract_images(self, media_items: List[Dict[str, Any]]) -> List[str]:
        """提取图片URL"""
        images = []
        for media in media_items:
            if media.get('type') == 'photo':
                media_url = media.get('media_url_https')
                if media_url:
                    images.append(media_url)
                    logging.debug(f"📸 提取图片: {media_url}")
        return images

    def _extract_videos(self, media_items: List[Dict[str, Any]]) -> List[str]:
        """提取视频URL"""
        videos = []
        for media in media_items:
            if media.get('type') in ['video', 'animated_gif']:
                video_url = self._extract_best_video_url(media)
                if video_url:
                    videos.append(video_url)
        return videos

    def _extract_best_video_url(self, media: Dict[str, Any]) -> Optional[str]:
        """提取最佳质量的视频URL"""
        video_info = media.get('video_info', {})
        variants = video_info.get('variants', [])

        mp4_variants = [v for v in variants if v.get('content_type') == 'video/mp4']
        if not mp4_variants:
            return None

        best_variant = max(mp4_variants, key=lambda x: x.get('bitrate', 0))
        logging.debug(f"🎬 提取视频: {best_variant['url'][:50]}...")
        return best_variant['url']

    def _extract_urls(self, item: Dict[str, Any]) -> List[str]:
        """提取扩展URL"""
        expand_urls = []
        urls = self._safe_get(item, 'legacy.entities.urls', [])
        for url in urls:
            expanded_url = url.get('expandedUrl')
            if expanded_url:
                expand_urls.append(expanded_url)
        return expand_urls

    def _build_tweet_url(self, user_info: Dict[str, str], item: Dict[str, Any]) -> str:
        """构造推文URL"""
        tweet_id = self._safe_get(item, 'legacy.id_str', '') or self._safe_get(item, 'rest_id', '')
        return f"https://x.com/{user_info['screenName']}/status/{tweet_id}"

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

    def tweet_cursor_generator(self, user_id: str, limit: int = 50, content_type: str = 'tweets') -> Generator[
        Dict[str, Any], None, None]:
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
                x_config = self.config.get('x', {})
                interval = x_config.get("delay_between_requests", 2)
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

    def process_user_tweets(self, user_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """处理用户推文的主流程 - 支持增量爬取和用户级配置"""
        screen_name = user_config['screen_name']
        start_time = time.time()
        self.logger.info("=" * 60)
        self.logger.info(f"🚀 开始处理用户 @{screen_name}")

        try:
            # 快速失败：获取用户信息
            user_info = self._get_user_info_for_processing(screen_name)
            if not user_info:
                return []

            # 获取爬取配置 (现在基于用户配置)
            crawl_config = self._prepare_crawl_config(user_config)
            if not crawl_config:
                return []

            # 处理推文数据
            all_tweets = self._process_tweets_with_incremental_crawl(user_info, crawl_config)

            # 保存结果并更新状态
            self._save_and_update_crawl_info(screen_name, all_tweets, start_time, user_info)

            return all_tweets

        except Exception as e:
            self.logger.error(f"❌ 处理用户 @{screen_name} 失败", error=str(e))
            return []

    def _get_user_info_for_processing(self, screen_name: str) -> Optional[Dict[str, Any]]:
        """获取用户信息 - 快速失败"""
        force_refresh = self.config.get_x_config().get('force_refresh', False)
        user_info = self.get_user_info(screen_name, force_refresh)

        if not user_info:
            logging.error(f"无法获取用户 @{screen_name} 的信息")
            return None

        return user_info

    def _prepare_crawl_config(self, user_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """根据用户配置准备爬取参数"""
        screen_name = user_config['screen_name']
        last_tweet_time = self._get_last_crawl_time(screen_name)

        # process_retweets: 0=不处理(过滤), 1=处理(不过滤)
        # filter_retweets: True=过滤, False=不过滤
        # 因此 filter_retweets = not process_retweets
        process_retweets = bool(user_config.get("process_retweets", False))
        filter_retweets = not process_retweets
        filter_quotes = bool(user_config.get("filter_quotes", True))

        self.logger.info("应用用户级爬取配置",
                         username=screen_name,
                         process_retweets=process_retweets,
                         filter_retweets=filter_retweets,
                         filter_quotes=filter_quotes)

        return {
            "max_tweets": self.config.get_x_config().get("max_tweets_per_user", 50),
            "filter_retweets": filter_retweets,
            "filter_quotes": filter_quotes,
            "content_type": "tweets",
            "last_tweet_time": last_tweet_time
        }

    def _get_last_crawl_time(self, screen_name: str) -> Optional[datetime]:
        """获取上次爬取时间"""
        if not self.db_manager:
            logging.info("🆕 数据库未初始化，获取所有推文")
            return None

        crawl_info = self.db_manager.get_user_last_crawl_info(screen_name)
        if crawl_info and 'last_tweet_time' in crawl_info:
            last_tweet_time = crawl_info['last_tweet_time']
            logging.info(f"📅 上次爬取的最新推文时间: {last_tweet_time}")
            logging.info("🔄 启用增量爬取模式，只获取新推文")
            return last_tweet_time
        else:
            logging.info("🆕 首次爬取该用户，获取所有推文")
            return None

    def _process_tweets_with_incremental_crawl(self, user_info: Dict[str, Any],
                                               crawl_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """处理推文数据，支持增量爬取"""
        all_tweets = []
        new_tweets_count = 0
        latest_tweet_time = None
        last_tweet_time = crawl_config.get("last_tweet_time")

        for item in self.tweet_cursor_generator(user_info['userId'],
                                                crawl_config["max_tweets"],
                                                crawl_config["content_type"]):

            # 处理单个推文项目
            tweet_data = self._process_single_tweet_item(item, user_info, crawl_config)
            if not tweet_data:
                continue

            # 检查是否应该停止爬取
            if self._should_stop_crawling(tweet_data, last_tweet_time, latest_tweet_time):
                break

            # 更新统计信息
            all_tweets.append(tweet_data)
            new_tweets_count = self._update_new_tweets_count(tweet_data, last_tweet_time, new_tweets_count)
            latest_tweet_time = self._update_latest_tweet_time(tweet_data, latest_tweet_time)

        logging.info(f"📊 处理完成 - 有效推文: {len(all_tweets)}, 新推文: {new_tweets_count}")
        return all_tweets

    def _process_single_tweet_item(self, item: Dict[str, Any], user_info: Dict[str, Any],
                                   crawl_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理单个推文项目"""
        tweet_data = self.transform_tweet(
            item,
            user_info['userId'],
            crawl_config["filter_retweets"],
            crawl_config["filter_quotes"]
        )

        return tweet_data if tweet_data else None

    def _should_stop_crawling(self, tweet_data: Dict[str, Any], last_tweet_time: Optional[datetime],
                              latest_tweet_time: Optional[datetime]) -> bool:
        """判断是否应该停止爬取"""
        if not last_tweet_time:
            return False

        tweet_time = self._parse_tweet_time(tweet_data.get('publishTime', ''))
        if not tweet_time:
            return False

        # 如果推文时间早于或等于上次爬取时间，停止爬取
        if tweet_time <= last_tweet_time:
            logging.info(f"⏹️ 遇到已爬取的推文 ({tweet_data.get('publishTime', '')})，停止爬取")
            return True

        return False

    def _parse_tweet_time(self, time_str: str) -> Optional[datetime]:
        """解析推文时间"""
        if not time_str:
            return None

        try:
            return datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S')
        except ValueError as e:
            logging.warning(f"⚠️ 推文时间解析失败: {time_str}, {e}")
            return None

    def _update_new_tweets_count(self, tweet_data: Dict[str, Any], last_tweet_time: Optional[datetime],
                                 current_count: int) -> int:
        """更新新推文计数"""
        if not last_tweet_time:
            return current_count + 1

        tweet_time = self._parse_tweet_time(tweet_data.get('publishTime', ''))
        if tweet_time and tweet_time > last_tweet_time:
            return current_count + 1

        return current_count

    def _update_latest_tweet_time(self, tweet_data: Dict[str, Any], current_latest: Optional[datetime]) -> Optional[
        datetime]:
        """更新最新推文时间"""
        tweet_time = self._parse_tweet_time(tweet_data.get('publishTime', ''))
        if not tweet_time:
            return current_latest

        if not current_latest or tweet_time > current_latest:
            return tweet_time

        return current_latest

    def _save_and_update_crawl_info(self, screen_name: str, all_tweets: List[Dict[str, Any]],
                                    start_time: float, user_info: Dict[str, Any]):
        """保存数据并更新爬取信息"""
        # 保存推文到数据库
        success_count = self.save_tweets_to_database(all_tweets) if all_tweets else 0
        logging.info(f"✅ 成功保存 {success_count} 条推文到数据库")

        # 更新爬取信息
        self._update_crawl_info(screen_name, all_tweets)

        # 输出统计信息
        self._log_processing_stats(screen_name, all_tweets, success_count, start_time, user_info)

    def _update_crawl_info(self, screen_name: str, all_tweets: List[Dict[str, Any]]):
        """更新爬取信息"""
        if not self.db_manager:
            logging.warning("⚠️ 数据库未初始化，无法更新爬取信息")
            return

        latest_tweet_time = self._get_latest_tweet_time_from_list(all_tweets)
        if latest_tweet_time:
            self.db_manager.update_user_crawl_info(screen_name, latest_tweet_time)
            logging.info(f"📝 更新用户最新推文时间: {latest_tweet_time}")
        else:
            self.db_manager.update_user_crawl_info(screen_name)
            logging.info("📝 更新用户爬取时间")

    def _get_latest_tweet_time_from_list(self, tweets: List[Dict[str, Any]]) -> Optional[datetime]:
        """从推文列表中获取最新时间"""
        latest_time = None
        for tweet in tweets:
            tweet_time = self._parse_tweet_time(tweet.get('publishTime', ''))
            if tweet_time and (not latest_time or tweet_time > latest_time):
                latest_time = tweet_time
        return latest_time

    def _log_processing_stats(self, screen_name: str, all_tweets: List[Dict[str, Any]],
                              success_count: int, start_time: float, user_info: Dict[str, Any]):
        """记录处理统计信息"""
        time_cost = (time.time() - start_time)
        latest_tweet_time = self._get_latest_tweet_time_from_list(all_tweets)

        logging.info(f"""
🎉 处理完成！
├── 用户：@{user_info['screenName']} (ID: {user_info['userId']})
├── 获取：{len(all_tweets)} 条有效推文
├── 保存：{success_count} 条到数据库
├── 最新推文时间：{latest_tweet_time or '无'}
├── 耗时：{time_cost:.1f} 秒
        """)

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
            x_config = self.config.get('x', {})
            output_file = x_config.get("output_file", "data/x/tweets.json")
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

    def get_users_to_crawl(self) -> List[Dict[str, Any]]:
        """获取需要爬取的用户列表并包含其个人配置"""
        try:
            users_to_crawl = []
            x_config = self.config.get('x', {})
            config_users = x_config.get("users", [])

            if config_users:
                self.logger.info("从配置文件加载指定用户", user_count=len(config_users))
                if not self.db_manager:
                    self.logger.error("数据库未初始化，无法获取用户配置")
                    return []
                for screen_name in config_users:
                    user_info = self.db_manager.get_user_last_crawl_info(screen_name)
                    if user_info:
                        users_to_crawl.append(user_info)
                    else:
                        self.logger.warning("在数据库中未找到配置的用户，无法获取其爬取配置", username=screen_name)
            else:
                self.logger.info("配置文件未指定用户，从数据库获取所有关注的用户")
                if self.db_manager:
                    users_to_crawl = self.db_manager.get_followed_users()

            if not users_to_crawl:
                self.logger.warning("未找到需要爬取的用户", action="检查配置或数据库")
                self.logger.info("配置提示",
                                 config_location="config.toml中的x.users",
                                 database_setting="member_x表中设置follow=1的用户")
                return []

            self.logger.info(f"共找到 {len(users_to_crawl)} 个待爬取用户")
            for user in users_to_crawl:
                self.logger.info("待爬取用户",
                                 username=user['screen_name'],
                                 process_retweets=user.get('process_retweets'),
                                 filter_quotes=user.get('filter_quotes'))
            return users_to_crawl

        except Exception as e:
            self.logger.error("获取待爬取用户列表失败", error=str(e))
            return []

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
        # 获取需要爬取的用户列表及其配置
        users_to_crawl = self.get_users_to_crawl()

        if not users_to_crawl:
            self.logger.error("❌ 没有找到需要爬取的用户，程序退出")
            return []

        self.logger.info("开始爬取用户推文", user_count=len(users_to_crawl))

        all_results = []

        try:
            for user_config in users_to_crawl:
                try:
                    # 处理单个用户
                    user_tweets = self.process_user_tweets(user_config)
                    all_results.extend(user_tweets)

                except Exception as e:
                    self.logger.error(f"处理用户 {user_config.get('screen_name')} 时出错", error=str(e))
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
    spider = XSpider()
    spider.run()
