from pathlib import Path
from sys import stdout
from loguru import logger

from conf import BASE_DIR


def log_formatter(record: dict) -> str:
    """
    Formatter for log records.
    :param dict record: Log object containing log metadata & message.
    :returns: str
    """
    colors = {
        "TRACE": "#cfe2f3",
        "INFO": "#9cbfdd",
        "DEBUG": "#8598ea",
        "WARNING": "#dcad5a",
        "SUCCESS": "#3dd08d",
        "ERROR": "#ae2c2c"
    }
    color = colors.get(record["level"].name, "#b3cfe7")
    return f"<fg #70acde>{{time:YYYY-MM-DD HH:mm:ss}}</fg #70acde> | <fg {color}>{{level}}</fg {color}>: <light-white>{{message}}</light-white>\n"


def create_logger(log_name: str, file_path: str = None):
    """
    Create custom logger for different business modules.
    :param str log_name: name of log
    :param str file_path: Optional path to log file
    :returns: Configured logger
    """
    def filter_record(record):
        return record["extra"].get("business_name") == log_name

    # 默认日志文件路径为 logs/{log_name}.log
    if file_path is None:
        file_path = f"logs/{log_name}.log"
    
    Path(BASE_DIR / file_path).parent.mkdir(exist_ok=True)
    logger.add(Path(BASE_DIR / file_path), filter=filter_record, level="INFO", rotation="10 MB", retention="10 days", backtrace=True, diagnose=True)
    return logger.bind(business_name=log_name)


# Remove all existing handlers
logger.remove()
# Add a standard console handler
logger.add(stdout, colorize=True, format=log_formatter)

# 全局日志记录器
global_logger = create_logger('global', 'logs/global.log')
# 平台特定日志记录器
douyin_logger = create_logger('douyin')
tencent_logger = create_logger('tencent')
xhs_logger = create_logger('xhs')
tiktok_logger = create_logger('tiktok')
bilibili_logger = create_logger('bilibili')
kuaishou_logger = create_logger('kuaishou')
baijiahao_logger = create_logger('baijiahao')
xiaohongshu_logger = create_logger('xiaohongshu')
# X平台日志记录器
x_logger = create_logger('x')
# 数据库日志记录器
database_logger = create_logger('database')
# 任务调度日志记录器
scheduler_logger = create_logger('scheduler')
# 爬虫日志记录器
spider_logger = create_logger('spider')
