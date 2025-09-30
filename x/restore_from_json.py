#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X平台推文数据还原脚本
从 tweets.json 文件中还原数据到数据库
"""

import json
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base.database import DatabaseManager
from base.logger import get_logger


def load_tweets_from_json(json_file_path):
    """从JSON文件加载推文数据"""
    logger = get_logger(__name__)
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            tweets = json.load(f)
        logger.info(f"✅ 成功加载 {len(tweets)} 条推文数据")
        return tweets
    except FileNotFoundError:
        logger.error(f"❌ 文件不存在: {json_file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON解析错误: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ 加载文件时出错: {e}")
        return []


def convert_tweet_format(tweet_data):
    """将JSON格式的推文数据转换为数据库格式"""
    try:
        # 处理图片列表
        images = tweet_data.get('images', [])
        images_str = ','.join(images) if images else None

        # 处理视频列表
        videos = tweet_data.get('videos', [])
        videos_str = ','.join(videos) if videos else None

        # 转换时间格式
        publish_time_str = tweet_data.get('publishTime', '')
        if publish_time_str:
            # 解析ISO格式时间
            publish_time = datetime.fromisoformat(publish_time_str.replace('Z', '+00:00'))
        else:
            publish_time = datetime.now()

        # 从tweetUrl提取tweetId
        tweet_url = tweet_data.get('tweetUrl', '')
        tweet_id = None
        if tweet_url and '/status/' in tweet_url:
            tweet_id = tweet_url.split('/status/')[-1].split('?')[0]

        return {
            'screenName': tweet_data.get('screenName', ''),
            'images': images_str,
            'videos': videos_str,
            'tweetUrl': tweet_url,
            'fullText': tweet_data.get('fullText', ''),
            'publishTime': publish_time,
            'tweetId': tweet_id
        }
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"❌ 转换推文数据时出错: {e}")
        logger.error(f"   原始数据: {tweet_data}")
        return None


def restore_tweets_to_database(tweets_data):
    """将推文数据还原到数据库"""
    logger = get_logger(__name__)
    db = DatabaseManager()

    success_count = 0
    error_count = 0
    duplicate_count = 0

    logger.info(f"🚀 开始还原 {len(tweets_data)} 条推文到数据库...")

    for i, tweet_data in enumerate(tweets_data, 1):
        try:
            # 转换数据格式
            converted_tweet = convert_tweet_format(tweet_data)
            if not converted_tweet:
                error_count += 1
                continue

            # 保存到数据库
            result = db.save_tweet(converted_tweet)

            if result:
                success_count += 1
                if i % 100 == 0:
                    logger.info(
                        f"📊 进度: {i}/{len(tweets_data)} - 成功: {success_count}, 重复: {duplicate_count}, 错误: {error_count}")
            else:
                duplicate_count += 1

        except Exception as e:
            error_count += 1
            logger.error(f"❌ 处理第 {i} 条推文时出错: {e}")
            continue

    logger.info(f"✅ 数据还原完成!")
    logger.info(f"📊 统计结果:")
    logger.info(f"   - 总数据量: {len(tweets_data)}")
    logger.info(f"   - 成功导入: {success_count}")
    logger.info(f"   - 重复跳过: {duplicate_count}")
    logger.info(f"   - 错误数量: {error_count}")

    return success_count, duplicate_count, error_count


def main():
    """主函数"""
    logger = get_logger(__name__)
    logger.info("🔄 X平台推文数据还原工具")
    logger.info("=" * 50)

    # JSON文件路径
    json_file_path = "data/x/tweets.json"

    # 检查文件是否存在
    if not os.path.exists(json_file_path):
        logger.error(f"❌ 文件不存在: {json_file_path}")
        return

    # 加载推文数据
    tweets_data = load_tweets_from_json(json_file_path)
    if not tweets_data:
        logger.error("❌ 没有可还原的数据")
        return

    # 显示数据预览
    logger.info(f"📋 数据预览 (前3条):")
    for i, tweet in enumerate(tweets_data[:3], 1):
        logger.info(f"  {i}. {tweet.get('screenName', 'Unknown')} - {tweet.get('publishTime', 'Unknown')}")
        logger.info(f"     {tweet.get('fullText', '')[:50]}...")
        if tweet.get('images'):
            logger.info(f"     📸 图片: {len(tweet['images'])}张")
        if tweet.get('videos'):
            logger.info(f"     🎥 视频: {len(tweet['videos'])}个")

    # 确认是否继续
    confirm = input(f"是否继续还原 {len(tweets_data)} 条推文到数据库? (y/N): ").strip().lower()
    if confirm != 'y':
        logger.warning("❌ 操作已取消")
        return

    # 执行数据还原
    restore_tweets_to_database(tweets_data)

    logger.info(f"🎉 数据还原任务完成!")


if __name__ == "__main__":
    main()
