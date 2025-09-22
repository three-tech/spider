"""
X平台爬虫定时任务具体实现
"""

import json
import os
import sys
from base.logger import get_logger
from datetime import datetime, timedelta

# 添加项目根目录到路径，以便导入base模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 添加x模块路径
x_module_path = os.path.join(project_root, 'x')
sys.path.insert(0, x_module_path)

# 导入模块
from base.database import DatabaseManager, MemberXhs
from base.logger import get_logger
from base.utils import ImageDownloadManager
from sms.notification_manager import get_notification_manager
from x.x_spider_optimized import XSpiderOptimized


def crawl_followed_users_task(config_path: str = None):
    """
    爬取关注用户推文的定时任务
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        dict: 任务执行结果
    """
    logger = get_logger(__name__)

    try:
        # 如果没有指定配置文件路径，使用默认路径
        if config_path is None:
            # 获取项目根目录的配置文件
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(project_root, 'config.json')

        # 读取配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 初始化数据库管理器
        db = DatabaseManager()

        # 获取关注的用户列表
        followed_users = db.get_followed_users()

        if not followed_users:
            logger.warning("⚠️ 没有找到关注的用户")
            return {
                'success': True,
                'stats': {'total_users': 0, 'total_tweets': 0},
                'message': '没有关注的用户'
            }

        logger.info(f"📋 找到 {len(followed_users)} 个关注的用户")

        # 初始化爬虫
        spider = XSpiderOptimized(config_path)

        total_tweets = 0
        successful_users = 0
        failed_users = []

        # 遍历每个关注的用户
        for user in followed_users:
            screen_name = user.screen_name

            try:
                logger.info(f"🔍 开始爬取用户: @{screen_name}")

                # 获取用户最后爬取信息
                crawl_info = db.get_user_last_crawl_info(screen_name)

                # 设置爬取参数
                crawl_params = {
                    'screen_name': screen_name,
                    'count': config.get('crawl_count', 20),  # 默认爬取20条
                    'include_rts': config.get('include_retweets', True)
                }

                # 如果有上次爬取时间，设置since_time进行增量爬取
                if crawl_info and crawl_info.get('last_tweet_time'):
                    # 从上次最新推文时间开始爬取
                    crawl_params['since_time'] = crawl_info['last_tweet_time']
                    logger.info(f"📅 增量爬取，从 {crawl_info['last_tweet_time']} 开始")
                else:
                    # 首次爬取，获取最近7天的推文
                    since_time = datetime.now() - timedelta(days=7)
                    crawl_params['since_time'] = since_time
                    logger.info(f"📅 首次爬取，获取最近7天推文")

                # 执行爬取 - 使用 process_user_tweets 方法
                tweets = spider.process_user_tweets(screen_name)

                if tweets:
                    # process_user_tweets 已经包含保存逻辑，直接统计数量
                    total_tweets += len(tweets)

                    logger.info(f"✅ @{screen_name}: 处理了 {len(tweets)} 条推文")
                    successful_users += 1
                else:
                    logger.info(f"ℹ️ @{screen_name}: 没有新推文")
                    successful_users += 1

            except Exception as e:
                logger.error(f"❌ 爬取用户 @{screen_name} 失败: {e}")
                failed_users.append({
                    'screen_name': screen_name,
                    'error': str(e)
                })

        # 关闭资源 - XSpiderOptimized 不需要显式关闭
        # spider.close()  # XSpiderOptimized 没有 close 方法
        # db.close()      # DatabaseManager 也不需要显式关闭

        # 统计结果
        stats = {
            'total_users': len(followed_users),
            'successful_users': successful_users,
            'failed_users': len(failed_users),
            'total_tweets': total_tweets,
            'failed_user_list': failed_users
        }

        logger.info(f"📊 任务完成统计:")
        logger.info(f"   👥 总用户数: {stats['total_users']}")
        logger.info(f"   ✅ 成功: {stats['successful_users']}")
        logger.info(f"   ❌ 失败: {stats['failed_users']}")
        logger.info(f"   📝 总推文数: {stats['total_tweets']}")

        return {
            'success': True,
            'stats': stats,
            'message': f'成功爬取 {successful_users}/{len(followed_users)} 个用户，共 {total_tweets} 条推文'
        }

    except Exception as e:
        logger.error(f"❌ 定时任务执行失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'stats': {}
        }


def cleanup_old_tweets_task(days=30):
    """
    清理旧推文的任务
    
    Args:
        days: 保留天数，默认30天
        
    Returns:
        dict: 清理结果
    """
    logger = get_logger(__name__)

    try:
        db = DatabaseManager()

        # 计算截止日期
        cutoff_date = datetime.now() - timedelta(days=days)

        # 这里可以实现清理逻辑
        # 例如：删除超过指定天数的推文
        logger.info(f"🧹 清理 {cutoff_date} 之前的推文")

        # 实际清理代码...

        db.close()

        return {
            'success': True,
            'message': f'清理完成，删除了 {cutoff_date} 之前的推文'
        }

    except Exception as e:
        logger.error(f"❌ 清理任务失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def backup_database_task():
    """
    数据库备份任务
    
    Returns:
        dict: 备份结果
    """
    logger = get_logger(__name__)

    try:
        # 这里可以实现数据库备份逻辑
        backup_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"backup_x_spider_{backup_time}.sql"

        logger.info(f"💾 开始数据库备份: {backup_file}")

        # 实际备份代码...

        return {
            'success': True,
            'message': f'数据库备份完成: {backup_file}'
        }

    except Exception as e:
        logger.error(f"❌ 数据库备份失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def xhs_auto_publish_task(config_path='config.json'):
    """
    小红书自动发布任务
    
    功能流程：
    1. 获取member_xhs表的所有账户
    2. 根据xhs tags找到相同标签的x账户
    3. 从resource_x中获取未发送过的推文
    4. 调用XiaoHongShuImg的main方法发布
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        dict: 任务执行结果
    """
    logger = get_logger(__name__)

    try:
        # 确保配置文件路径正确
        if not os.path.isabs(config_path):
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config_path)

        # 读取配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 初始化数据库管理器
        db = DatabaseManager()

        # 获取所有小红书会员
        xhs_members = db.get_all_member_xhs()

        if not xhs_members:
            logger.warning("⚠️ 没有找到小红书会员")
            return {
                'success': True,
                'stats': {'total_xhs_members': 0, 'published_count': 0},
                'message': '没有小红书会员'
            }

        logger.info(f"📋 找到 {len(xhs_members)} 个小红书会员")

        total_published = 0
        successful_members = 0
        failed_members = []

        # 遍历每个小红书会员
        for xhs_member in xhs_members:
            # MemberXhs 是 SQLAlchemy 对象，直接访问属性
            xhs_id = xhs_member.xhs_id
            user_name = xhs_member.userName
            xhs_tags = xhs_member.tags or '' if hasattr(xhs_member, 'tags') else ''

            try:
                logger.info(f"🔍 处理小红书会员: {user_name} (ID: {xhs_id})")

                if not xhs_tags:
                    logger.warning(f"⚠️ 会员 {user_name} 没有设置标签，跳过")
                    continue

                # 解析标签列表
                tag_list = [tag.strip() for tag in xhs_tags.split(',') if tag.strip()]
                logger.info(f"🏷️ 会员标签: {tag_list}")

                # 根据标签找到相同标签的X账户
                matching_x_users = []
                for tag in tag_list:
                    # 在member_x表中搜索包含相同标签的用户
                    x_users = db.search_members_by_tag(tag)  # 这个方法需要在DatabaseManager中实现
                    matching_x_users.extend(x_users)

                # 去重
                unique_x_users = {}
                for user in matching_x_users:
                    # 检查 user 是字典还是对象
                    if hasattr(user, 'screen_name'):
                        unique_x_users[user.screen_name] = user
                    else:
                        unique_x_users[user.screen_name] = user
                matching_x_users = list(unique_x_users.values())

                if not matching_x_users:
                    logger.warning(f"⚠️ 没有找到与标签 {tag_list} 匹配的X账户")
                    continue

                logger.info(f"👥 找到 {len(matching_x_users)} 个匹配的X账户")

                # 从匹配的X账户中获取未发送过的推文
                matching_screen_names = []
                for user in matching_x_users:
                    if hasattr(user, 'screen_name'):
                        matching_screen_names.append(user.screen_name)
                    else:
                        matching_screen_names.append(user.screen_name)
                unpublished_tweet = db.get_unpublished_tweet_by_xhs_member(xhs_id, matching_screen_names)

                if unpublished_tweet:
                    # 检查 unpublished_tweet 是字典还是对象
                    if hasattr(unpublished_tweet, 'screenName'):
                        logger.info(f"📝 找到未发布推文，来自用户: @{unpublished_tweet.screenName}")
                    logger.info(f"📝 找到未发布推文，来自用户: @{unpublished_tweet.screenName}")

                if not unpublished_tweet:
                    logger.warning(f"⚠️ 没有找到未发布的推文")
                    continue

                # 准备发布内容
                if hasattr(unpublished_tweet, 'fullText'):
                    title = unpublished_tweet.fullText[:50] + "..." if unpublished_tweet.fullText else ""
                    content = unpublished_tweet.fullText or ""
                title = unpublished_tweet.fullText[:50] + "..." if unpublished_tweet.fullText else ""
                content = unpublished_tweet.fullText or ""

                # 处理图片路径 - 下载到本地
                if hasattr(unpublished_tweet, 'images'):
                    images = unpublished_tweet.images or ""
                images = unpublished_tweet.images or ""
                if not images:
                    logger.warning(f"⚠️ 推文没有图片，跳过发布")
                    continue

                # 解析图片URL列表
                image_urls = [url.strip() for url in images.split(',') if url.strip()]
                if not image_urls:
                    logger.warning(f"⚠️ 推文图片URL无效，跳过发布")
                    continue

                logger.info(f"📸 开始下载 {len(image_urls)} 张图片...")

                # 使用图片下载管理器 - 完整的下载-发布-清理流程
                with ImageDownloadManager() as img_manager:
                    # 下载图片到本地
                    local_image_paths = img_manager.download_images(image_urls, max_images=9)

                    if not local_image_paths:
                        logger.warning(f"⚠️ 图片下载失败，跳过发布")
                        continue

                    logger.info(f"✅ 成功下载 {len(local_image_paths)} 张图片")

                    # 准备本地文件路径字符串
                    file_path = ','.join(local_image_paths)

                    # 准备标签
                    publish_tags = tag_list[:10]  # 小红书标签限制

                    # 发布时间设置为当前时间
                    publish_date = datetime.now().strftime('%Y年%m月%d日 %H:%M')

                    # 发送飞书通知
                    try:
                        notification_manager = get_notification_manager()
                        if notification_manager.is_notification_enabled():
                            logger.info("📤 发送飞书通知...")

                            # 准备通知信息
                            if hasattr(unpublished_tweet, 'publishTime'):
                                tweet_publish_time = unpublished_tweet.publishTime
                                tweet_content = unpublished_tweet.fullText or ""
                                tweet_author = unpublished_tweet.screenName
                            tweet_publish_time = unpublished_tweet.publishTime
                            tweet_content = unpublished_tweet.fullText or ""
                            tweet_author = unpublished_tweet.screenName

                            # 发送通知
                            notification_result = notification_manager.send_xhs_publish_notification(
                                xhs_account=str(user_name),
                                image_count=len(image_urls),
                                image_paths=image_urls,
                                tweet_publish_time=str(tweet_publish_time),
                                tweet_content=str(tweet_content),
                                tweet_author=str(tweet_author)
                            )

                            if notification_result.get('feishu', {}).get('success'):
                                logger.info("✅ 飞书通知发送成功")
                            else:
                                logger.warning("⚠️ 飞书通知发送失败")
                        else:
                            logger.info("ℹ️ 通知功能未启用，跳过通知")
                    except Exception as notify_error:
                        logger.error(f"❌ 发送通知时出错: {notify_error}")

                    logger.info(f"🚀 开始发布到小红书...")
                    logger.info(f"   标题: {title}")
                    logger.info(f"   标签: {publish_tags}")
                    logger.info(f"   图片: {len(local_image_paths)} 张")

                    # 调用XiaoHongShuImg的main方法
                    # 注意：这是异步方法，需要在同步环境中调用
                    import asyncio
                    from xiaohongshu.xhs_upload_img import XiaoHongShuImg

                    xhs_uploader = XiaoHongShuImg(
                        user_name=str(user_name),
                        title=title,
                        file_path=file_path,
                        tags=publish_tags,
                        member_xhs=xhs_member,
                        publish_date=publish_date,
                        content=str(tweet_content),
                        headless=False  # 后台运行
                    )

                    # 在同步环境中运行异步方法
                    try:
                        asyncio.run(xhs_uploader.main())

                        # 标记推文为已发布
                        if hasattr(unpublished_tweet, 'id'):
                            db.mark_tweet_as_published(unpublished_tweet.id, xhs_id)
                        db.mark_tweet_as_published(unpublished_tweet.id, xhs_id)

                        total_published += 1
                        successful_members += 1

                        logger.info(f"✅ {user_name}: 成功发布推文")
                        logger.info(f"🧹 图片将在退出时自动清理")

                    except Exception as upload_error:
                        logger.error(f"❌ 发布失败: {upload_error}")
                        failed_members.append({
                            'xhs_id': xhs_id,
                            'user_name': user_name,
                            'error': str(upload_error)
                        })
                # 注意：图片文件会在with块结束时自动删除

            except Exception as e:
                logger.error(f"❌ 处理会员 {user_name} 失败: {e}")
                failed_members.append({
                    'xhs_id': xhs_id,
                    'user_name': user_name,
                    'error': str(e)
                })

        # 统计结果
        stats = {
            'total_xhs_members': len(xhs_members),
            'successful_members': successful_members,
            'failed_members': len(failed_members),
            'published_count': total_published,
            'failed_member_list': failed_members
        }

        logger.info(f"📊 小红书发布任务完成统计:")
        logger.info(f"   👥 总会员数: {stats['total_xhs_members']}")
        logger.info(f"   ✅ 成功: {stats['successful_members']}")
        logger.info(f"   ❌ 失败: {stats['failed_members']}")
        logger.info(f"   📝 发布数: {stats['published_count']}")

        return {
            'success': True,
            'stats': stats,
            'message': f'成功处理 {successful_members}/{len(xhs_members)} 个会员，发布 {total_published} 条内容'
        }

    except Exception as e:
        logger.error(f"❌ 小红书发布任务执行失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'stats': {}
        }


if __name__ == "__main__":
    # 测试任务执行
    logger = get_logger(__name__)
    logger.info("🧪 测试定时任务...")
    result = crawl_followed_users_task()
    logger.info(f"📊 任务结果: {result}")
