#!/usr/bin/env python3
"""
X平台爬虫定时任务运行器
"""

import sys
import os
import argparse
import time
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 添加x模块路径
x_module_path = os.path.join(project_root, 'x')
sys.path.insert(0, x_module_path)

# 添加当前job目录到路径
job_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, job_path)

from .scheduler import XSpiderScheduler
from base.logger import get_logger

def main():
    """主函数"""
    logger = get_logger(__name__)
    parser = argparse.ArgumentParser(description='X平台爬虫定时任务调度器')
    parser.add_argument('--config', '-c', default=None, help='配置文件路径（向后兼容，现在通过ConfigManager统一管理）')
    parser.add_argument('--list-jobs', action='store_true', help='列出所有定时任务')
    parser.add_argument('--run-now', action='store_true', help='立即执行一次爬取任务')
    parser.add_argument('--daemon', '-d', action='store_true', help='以守护进程模式运行')
    
    args = parser.parse_args()
    
    # 初始化调度器
    scheduler = XSpiderScheduler(args.config)
    
    if args.list_jobs:
        # 列出所有任务
        logger.info("📋 定时任务列表:")
        scheduler.setup_jobs()
        jobs = scheduler.list_jobs()
        
        if jobs:
            for i, job in enumerate(jobs, 1):
                logger.info(f"  {i}. {job.job}")
                logger.info(f"     ⏰ 下次运行: {job.next_run}")
                logger.info(f"     🔄 间隔: 每{job.interval}{job.unit}")
        else:
            logger.info("  暂无定时任务")
            
    elif args.run_now:
        # 立即执行任务
        logger.info("🚀 立即执行爬取任务...")
        scheduler.run_now()
        
    elif args.daemon:
        # 守护进程模式
        logger.info("🎯 启动X平台爬虫调度器（守护进程模式）...")
        scheduler.start()
        
        try:
            # 显示下次运行时间
            next_run = scheduler.get_next_run_time()
            if next_run:
                logger.info(f"📅 下次运行时间: {next_run}")
            
            logger.info("🔄 调度器正在运行中，按 Ctrl+C 停止...")
            
            # 保持程序运行
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 收到停止信号，正在关闭调度器...")
            scheduler.stop()
            logger.info("✅ 调度器已停止")
            
    else:
        # 显示帮助信息
        parser.print_help()
        logger.info("\n📖 使用示例:")
        logger.info("  python3 run_scheduler.py --list-jobs     # 查看定时任务")
        logger.info("  python3 run_scheduler.py --run-now       # 立即执行一次")
        logger.info("  python3 run_scheduler.py --daemon        # 启动守护进程")

if __name__ == "__main__":
    main()