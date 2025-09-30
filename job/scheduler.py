"""
X平台爬虫定时任务调度器
"""

import schedule
import time
import threading
from datetime import datetime
from .tasks import crawl_followed_users_task, xhs_auto_publish_task
from base.logger import get_logger

class XSpiderScheduler:
    """X平台爬虫定时任务调度器"""
    
    def __init__(self, config_path=None):
        """
        初始化调度器
        
        Args:
            config_path: 配置文件路径（向后兼容，现在通过ConfigManager统一管理）
        """
        self.config_path = config_path  # 保持向后兼容
        self.running = False
        self.scheduler_thread = None
        
        # 配置日志 - 使用统一的loguru日志系统
        from base.logger import get_logger
        self.logger = get_logger(__name__)
        
    def setup_jobs(self):
        """设置定时任务"""
        # 每天早晨6点执行关注用户推文爬取任务
        schedule.every().day.at("06:00").do(self._run_crawl_task)
        
        # 小红书自动发布任务 - 每天早晨8点前后半小时内执行
        schedule.every().day.at("08:30").do(self._run_xhs_publish_task)
        
        # 小红书自动发布任务 - 每天下午6点前后半小时内执行
        schedule.every().day.at("18:30").do(self._run_xhs_publish_task)
        
        # 可以添加更多定时任务
        # schedule.every().hour.do(self._run_hourly_task)  # 每小时执行
        # schedule.every().monday.at("09:00").do(self._run_weekly_task)  # 每周一9点执行
        
        self.logger.info("✅ 定时任务设置完成")
        self.logger.info("📅 每日6:00 - 自动爬取关注用户推文")
        self.logger.info("📅 每日7:30/8:00/8:30 - 小红书自动发布")
        self.logger.info("📅 每日17:30/18:00/18:30 - 小红书自动发布")
        
    def _run_crawl_task(self):
        """执行爬取任务的包装方法"""
        try:
            self.logger.info("🚀 开始执行定时爬取任务...")
            start_time = datetime.now()
            
            # 执行爬取任务（向后兼容，传递config_path参数）
            result = crawl_followed_users_task(str(self.config_path) if self.config_path else None)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if result.get('success'):
                self.logger.info(f"✅ 定时爬取任务完成！")
                self.logger.info(f"📊 爬取统计: {result.get('stats', {})}")
                self.logger.info(f"⏱️ 耗时: {duration:.2f}秒")
            else:
                self.logger.error(f"❌ 定时爬取任务失败: {result.get('error', '未知错误')}")
                
        except Exception as e:
            self.logger.error(f"❌ 定时任务执行异常: {e}")
    
    def _run_xhs_publish_task(self):
        """执行小红书发布任务的包装方法"""
        try:
            self.logger.info("🚀 开始执行小红书自动发布任务...")
            start_time = datetime.now()
            
            # 执行小红书发布任务（向后兼容，传递config_path参数）
            result = xhs_auto_publish_task(str(self.config_path) if self.config_path else None)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if result.get('success'):
                self.logger.info(f"✅ 小红书发布任务完成！")
                self.logger.info(f"📊 发布统计: {result.get('stats', {})}")
                self.logger.info(f"⏱️ 耗时: {duration:.2f}秒")
            else:
                self.logger.error(f"❌ 小红书发布任务失败: {result.get('error', '未知错误')}")
                
        except Exception as e:
            self.logger.error(f"❌ 小红书发布任务执行异常: {e}")
    
    def start(self):
        """启动调度器"""
        if self.running:
            self.logger.warning("⚠️ 调度器已在运行中")
            return
            
        self.setup_jobs()
        self.running = True
        
        # 在单独线程中运行调度器
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info("🎯 X平台爬虫调度器已启动")
        
    def _run_scheduler(self):
        """运行调度器主循环"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                self.logger.error(f"❌ 调度器运行异常: {e}")
                time.sleep(60)
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        # 清除所有任务
        schedule.clear()
        self.logger.info("🛑 X平台爬虫调度器已停止")
    
    def get_next_run_time(self):
        """获取下次运行时间"""
        jobs = schedule.get_jobs()
        if jobs:
            next_run = min(job.next_run for job in jobs)
            return next_run
        return None
    
    def list_jobs(self):
        """列出所有定时任务"""
        jobs = schedule.get_jobs()
        job_info = []
        
        for job in jobs:
            job_info.append({
                'job': str(job.job_func),
                'next_run': job.next_run,
                'interval': job.interval,
                'unit': job.unit
            })
            
        return job_info
    
    def run_now(self):
        """立即执行一次爬取任务"""
        self.logger.info("🚀 手动触发爬取任务...")
        self._run_crawl_task()
    
    def run_xhs_publish_now(self):
        """立即执行一次小红书发布任务"""
        self.logger.info("🚀 手动触发小红书发布任务...")
        self._run_xhs_publish_task()

if __name__ == "__main__":
    # 示例用法
    logger = get_logger(__name__)
    scheduler = XSpiderScheduler()
    
    try:
        scheduler.start()
        
        # 显示下次运行时间
        next_run = scheduler.get_next_run_time()
        if next_run:
            logger.info(f"📅 下次运行时间: {next_run}")
        
        # 保持程序运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 收到停止信号，正在关闭调度器...")
        scheduler.stop()
        logger.info("✅ 调度器已停止")