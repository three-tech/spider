#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试小红书自动发布任务
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.logger import get_logger
from tasks import xhs_auto_publish_task

def test_xhs_publish():
    """测试小红书发布任务"""
    logger = get_logger(__name__)
    
    logger.info("🧪 开始测试小红书自动发布任务...")
    
    try:
        # 执行小红书发布任务
        result = xhs_auto_publish_task()
        
        logger.info("📊 任务执行结果:")
        logger.info(f"   成功: {result.get('success')}")
        logger.info(f"   统计: {result.get('stats', {})}")
        logger.info(f"   消息: {result.get('message', '')}")
        
        if not result.get('success'):
            logger.error(f"   错误: {result.get('error', '未知错误')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 测试执行失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    test_xhs_publish()