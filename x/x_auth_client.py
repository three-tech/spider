#!/usr/bin/env python3
"""
X认证客户端 - 完全参考TypeScript版本的twitter-openapi-typescript实现
基于Cookie认证的Twitter API客户端
"""

import json

import requests

from base.logger import get_logger

logging = get_logger('x')
from typing import Dict, Optional, Any
import time


class XAuthClient:
    """X平台认证客户端 - 完全模拟TypeScript _xClient函数"""

    def __init__(self, auth_token: str):
        """
        初始化X认证客户端 - 完全按照TypeScript utils.ts的_xClient函数
        
        Args:
            auth_token: Twitter的auth_token Cookie值
        """
        self.auth_token = auth_token
        self.session = requests.Session()
        self.cookies = {}
        self.csrf_token = ""
        self.bearer_token = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

        # 完全按照TypeScript流程初始化
        self.initialize_client()

    def initialize_client(self):
        """初始化客户端 - 完全按照TypeScript _xClient函数的流程"""
        try:
            logging.info("🔄 正在初始化X客户端...")

            # 步骤1: 访问manifest.json - 完全按照TypeScript代码
            resp = self.session.get(
                "https://x.com/manifest.json",
                headers={
                    "cookie": f"auth_token={self.auth_token}",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )

            if resp.status_code != 200:
                raise Exception(f"访问manifest.json失败: {resp.status_code}")

            # 步骤2: 解析set-cookie - 完全按照TypeScript逻辑
            res_cookies = resp.headers.get('set-cookie', '')
            if res_cookies:
                # 按照TypeScript的reduce逻辑解析cookie
                cookie_parts = res_cookies.split(',')
                for cookie_part in cookie_parts:
                    # 取第一个分号前的部分
                    main_part = cookie_part.split(';')[0].strip()
                    if '=' in main_part:
                        name, value = main_part.split('=', 1)
                        name = name.strip()
                        value = value.strip()
                        # 过滤掉无效的cookie属性
                        if name and not name.lower().startswith(
                                ('path', 'domain', 'expires', 'max-age', 'secure', 'httponly', 'samesite')):
                            self.cookies[name] = value

            # 步骤3: 确保auth_token在cookies中 - 按照TypeScript逻辑
            self.cookies['auth_token'] = self.auth_token

            # 步骤4: 提取CSRF token
            self.csrf_token = self.cookies.get('ct0', '')

            # 步骤5: 设置会话
            self.setup_session()

            logging.info("✅ X认证客户端初始化成功")
            logging.info(f"Cookie数量: {len(self.cookies)}")
            if self.csrf_token:
                logging.info(f"CSRF Token: {self.csrf_token[:10]}...")

        except Exception as e:
            logging.error(f"❌ X客户端初始化失败: {e}")
            raise

    def setup_session(self):
        """设置会话 - 模拟twitter-openapi-typescript的请求头"""
        # 构建Cookie字符串
        cookie_str = '; '.join([f"{k}={v}" for k, v in self.cookies.items()])

        # 设置完整的请求头
        self.session.headers.update({
            "authorization": f"Bearer {self.bearer_token}",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "en",
            "cookie": cookie_str,
            "referer": "https://x.com/",
            "origin": "https://x.com",
        })

        # 如果有CSRF token，设置到header中
        if self.csrf_token:
            self.session.headers["x-csrf-token"] = self.csrf_token

    def get_user_by_screen_name(self, screen_name: str) -> Optional[Dict[str, Any]]:
        """
        通过用户名获取用户信息 - 使用正确的认证流程
        """
        try:
            # 使用正确的GraphQL端点
            url = "https://x.com/i/api/graphql/G3KGOASz96M-Qu0nwmGXNg/UserByScreenName"

            variables = {
                "screen_name": screen_name,
                "withSafetyModeUserFields": True
            }

            features = {
                "hidden_profile_likes_enabled": True,
                "hidden_profile_subscriptions_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "subscriptions_verification_info_is_identity_verified_enabled": True,
                "subscriptions_verification_info_verified_since_enabled": True,
                "highlights_tweets_tab_ui_enabled": True,
                "responsive_web_twitter_article_notes_tab_enabled": True,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True
            }

            params = {
                "variables": json.dumps(variables, separators=(',', ':')),
                "features": json.dumps(features, separators=(',', ':'))
            }

            logging.info(f"🔍 请求用户信息: @{screen_name}")
            if self.csrf_token:
                logging.info(f"CSRF Token: {self.csrf_token[:10]}...")
            else:
                logging.warning("⚠️ 没有CSRF token")

            response = self.session.get(url, params=params)

            logging.info(f"API请求状态: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                # 提取用户信息
                user_data = data.get('data', {}).get('user', {})
                if user_data and 'result' in user_data:
                    user_result = user_data['result']
                    if user_result.get('__typename') == 'User':
                        legacy = user_result.get('legacy', {})
                        return {
                            'id_str': user_result.get('rest_id'),
                            'screen_name': legacy.get('screen_name'),
                            'name': legacy.get('name'),
                            'description': legacy.get('description'),
                            'followers_count': legacy.get('followers_count'),
                            'friends_count': legacy.get('friends_count'),
                            'statuses_count': legacy.get('statuses_count'),
                            'created_at': legacy.get('created_at'),
                            'profile_image_url_https': legacy.get('profile_image_url_https')
                        }

                logging.error(f"用户数据格式异常: {json.dumps(data, indent=2)[:500]}...")
                return None
            else:
                error_text = response.text[:500] if response.text else "No response body"
                logging.error(f"获取用户信息失败: {response.status_code} - {error_text}")
                return None

        except Exception as e:
            logging.error(f"获取用户信息异常: {e}")
            return None

    def get_user_tweets(self, user_id: str, cursor: Optional[str] = None, count: int = 20) -> Optional[Dict[str, Any]]:
        """
        获取用户推文 - 使用正确的GraphQL端点
        """
        try:
            url = "https://x.com/i/api/graphql/V7H0Ap3_Hh2FyS75OCDO3Q/UserTweets"

            variables = {
                "userId": user_id,
                "count": count,
                "includePromotedContent": True,
                "withQuickPromoteEligibilityTweetFields": True,
                "withVoice": True,
                "withV2Timeline": True
            }

            if cursor:
                variables["cursor"] = cursor

            features = {
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_data_v2_enabled": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "rweb_video_timestamps_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_enhance_cards_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "articles_preview_enabled": True,
                "communities_web_enable_tweet_community_results_fetch": True,
                "standardized_nudges_misinfo": True,
                "creator_subscriptions_quote_tweet_preview_enabled": True,
                "rweb_tipjar_consumption_enabled": True
            }

            params = {
                "variables": json.dumps(variables, separators=(',', ':')),
                "features": json.dumps(features, separators=(',', ':'))
            }

            response = self.session.get(url, params=params)

            if response.status_code == 200:
                data = response.json()

                # 提取推文数据
                timeline = data.get('data', {}).get('user', {}).get('result', {}).get('timeline_v2', {})
                timeline_timeline = timeline.get('timeline', {})
                instructions = timeline_timeline.get('instructions', [])

                tweets = []
                next_cursor = None

                for instruction in instructions:
                    if instruction.get('type') == 'TimelineAddEntries':
                        entries = instruction.get('entries', [])
                        for entry in entries:
                            entry_id = entry.get('entryId', '')
                            if entry_id.startswith('tweet-'):
                                content = entry.get('content', {})
                                item_content = content.get('itemContent', {})
                                tweet_results = item_content.get('tweet_results', {})
                                result = tweet_results.get('result', {})
                                if result.get('__typename') == 'Tweet':
                                    tweets.append(result)
                            elif entry_id.startswith('cursor-bottom-'):
                                cursor_content = entry.get('content', {})
                                next_cursor = cursor_content.get('value')

                return {
                    'data': tweets,
                    'cursor': next_cursor
                }
            else:
                error_text = response.text[:500] if response.text else "No response body"
                logging.error(f"获取推文失败: {response.status_code} - {error_text}")
                return None

        except Exception as e:
            logging.error(f"获取推文异常: {e}")
            return None

    def get_my_following(self):
        """获取我的完整关注列表 - 循环获取所有用户"""
        try:
            logging.info("🔍 开始获取完整关注列表...")

            # 获取当前用户信息
            current_user = self.get_current_user_info()
            if not current_user:
                logging.error("❌ 无法获取当前用户信息")
                return None

            user_id = current_user.get('id_str')
            if not user_id:
                logging.error("❌ 无法从当前用户信息中获取用户ID")
                return None

            logging.info(f"✅ 获取到当前用户ID: {user_id}")

            # 初始化循环变量
            all_users = []
            cursor = None
            page_count = 0
            empty_count = 0
            request_interval = 3  # 请求间隔（秒）

            while True:
                page_count += 1
                logging.info(f"\n=== 第 {page_count} 次请求 ===")

                # 添加间隔控制（第一页后生效）
                if page_count > 1:
                    logging.info(f"⏸️ 等待 {request_interval} 秒...")
                    time.sleep(request_interval)

                # 构建GraphQL查询参数
                variables = {
                    "userId": user_id,
                    "count": 20,  # 每页固定20个用户
                    "includePromotedContent": False
                }

                if cursor:
                    variables["cursor"] = cursor
                    logging.info(f"📍 使用游标: {cursor}")

                features = {
                    "rweb_tipjar_consumption_enabled": True,
                    "responsive_web_graphql_exclude_directive_enabled": True,
                    "verified_phone_label_enabled": False,
                    "creator_subscriptions_tweet_preview_api_enabled": True,
                    "responsive_web_graphql_timeline_navigation_enabled": True,
                    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                    "communities_web_enable_tweet_community_results_fetch": True,
                    "c9s_tweet_anatomy_moderator_badge_enabled": True,
                    "articles_preview_enabled": True,
                    "tweetypie_unmention_optimization_enabled": True,
                    "responsive_web_edit_tweet_api_enabled": True,
                    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                    "view_counts_everywhere_api_enabled": True,
                    "longform_notetweets_consumption_enabled": True,
                    "responsive_web_twitter_article_tweet_consumption_enabled": True,
                    "tweet_awards_web_tipping_enabled": False,
                    "creator_subscriptions_quote_tweet_preview_enabled": False,
                    "freedom_of_speech_not_reach_fetch_enabled": True,
                    "standardized_nudges_misinfo": True,
                    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                    "rweb_video_timestamps_enabled": True,
                    "longform_notetweets_rich_text_read_enabled": True,
                    "longform_notetweets_inline_media_enabled": True,
                    "responsive_web_enhance_cards_enabled": False,
                    "responsive_web_media_download_video_enabled": True,
                    "responsive_web_text_conversations_enabled": False,
                    "blue_business_profile_image_shape_enabled": True,
                    "responsive_web_twitter_article_data_v2_enabled": True
                }

                # 构建请求参数
                params = {
                    'variables': json.dumps(variables),
                    'features': json.dumps(features)
                }

                # 发送请求
                url = "https://x.com/i/api/graphql/iSicc7LrzWGBgDPL0tM_TQ/Following"

                response = self.session.get(url, params=params)
                logging.info(f"API请求状态: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()

                    # 解析关注用户数据
                    if 'data' in data and 'user' in data['data'] and 'result' in data['data']['user']:
                        timeline = data['data']['user']['result'].get('timeline', {})
                        timeline_data = timeline.get('timeline', {})
                        instructions = timeline_data.get('instructions', [])

                        current_users = []
                        next_cursor = None

                        for instruction in instructions:
                            if instruction.get('type') == 'TimelineAddEntries':
                                entries = instruction.get('entries', [])
                                for entry in entries:
                                    entry_id = entry.get('entryId', '')
                                    if entry_id.startswith('user-'):
                                        content = entry.get('content', {})
                                        item_content = content.get('itemContent', {})
                                        user_results = item_content.get('user_results', {})
                                        user_result = user_results.get('result', {})

                                        if user_result.get('__typename') == 'User':
                                            legacy = user_result.get('legacy', {})
                                            user_info = {
                                                'id_str': user_result.get('rest_id', ''),
                                                'screen_name': legacy.get('screen_name', ''),
                                                'name': legacy.get('name', ''),
                                                'description': legacy.get('description', ''),
                                                'followers_count': legacy.get('followers_count', 0),
                                                'friends_count': legacy.get('friends_count', 0),
                                                'statuses_count': legacy.get('statuses_count', 0),
                                                'verified': legacy.get('verified', False),
                                                'profile_image_url_https': legacy.get('profile_image_url_https', ''),
                                                'profile_banner_url': legacy.get('profile_banner_url', ''),
                                                'location': legacy.get('location', ''),
                                                'url': legacy.get('url', ''),
                                                'created_at': legacy.get('created_at', ''),
                                                'protected': legacy.get('protected', False)
                                            }
                                            current_users.append(user_info)
                                    elif entry_id.startswith('cursor-bottom-'):
                                        cursor_content = entry.get('content', {})
                                        next_cursor = cursor_content.get('value')

                        # 检查是否获取到用户
                        if len(current_users) == 0:
                            empty_count += 1
                            logging.info(f"⚠️ 空响应计数: {empty_count}/3")
                            if empty_count >= 3:
                                logging.info("⏹️ 终止原因：连续3次空响应")
                                break
                        else:
                            empty_count = 0  # 重置计数器
                            all_users.extend(current_users)
                            logging.info(f"✅ 获取到 {len(current_users)} 个用户 | 游标: {next_cursor or '无'}")

                            # 优化：当返回用户数少于预期时，说明已接近末尾
                            if len(current_users) < 20:  # 每页期望20个用户
                                logging.info(
                                    f"⏹️ 终止原因：返回用户数({len(current_users)})少于预期(20)，已获取完所有数据")
                                break

                        # 更新游标
                        cursor = next_cursor
                        if not cursor:
                            logging.info("⏹️ 终止原因：无更多数据")
                            break
                    else:
                        logging.error("❌ 响应数据格式不正确")
                        break
                else:
                    error_text = response.text[:500] if response.text else "No response body"
                    logging.error(f"获取关注列表失败: {response.status_code} - {error_text}")
                    break

            logging.info(f"🎉 完成！共获取 {len(all_users)} 个关注用户")
            return {
                'users': all_users,
                'count': len(all_users)
            }

        except Exception as e:
            logging.error(f"获取关注列表时出错: {e}")
            return None

    def get_current_user_info(self, screen_name: str = None) -> Optional[Dict[str, Any]]:
        """
        获取当前认证用户的信息
        
        Args:
            screen_name: 可选的用户名，如果不提供则尝试从配置中获取
        """
        try:
            # 如果没有提供screen_name，尝试从配置文件中读取
            if not screen_name:
                try:
                    from base.config import config
                    screen_name = config.get_x_config().get('current_user_screen_name')
                except Exception as e:
                    logging.warning(f"无法从配置文件读取用户名: {e}")

            # 如果仍然没有screen_name，使用一个默认的方法
            if not screen_name:
                logging.error("❌ 无法确定当前用户的screen_name，请在配置文件中添加 'current_user_screen_name' 字段")
                return None

            logging.info(f"🔍 获取用户信息: @{screen_name}")

            # 使用现有的get_user_by_screen_name方法
            return self.get_user_by_screen_name(screen_name)

        except Exception as e:
            logging.error(f"获取当前用户信息异常: {e}")
            return None


def create_x_auth_client(auth_token: str) -> XAuthClient:
    """
    创建X认证客户端 - 参考TypeScript版本的XAuthClient函数
    
    Args:
        auth_token: Twitter的auth_token Cookie值
        
    Returns:
        XAuthClient实例
    """
    return XAuthClient(auth_token)
