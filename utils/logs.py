import datetime
import logging
import os
import re
import sys
# 获取当前文件的绝对路径
current_file_path = os.path.abspath(__file__)
# 获取项目根目录路径
project_root = os.path.dirname(os.path.dirname(current_file_path))
# 获取工程名
project_name = os.path.basename(project_root)

class MultiprocessHandler(logging.FileHandler):
    """
    Say something about the ExampleCalass...

    Args:
        args_0 (`type`):
        ...
    """

    def __init__(self, filename, when="D", backupCount=0, encoding=None, delay=False):
        self.prefix = filename
        self.backupCount = backupCount
        self.when = when.upper()
        self.extMath = r"^\d{4}-\d{2}-\d{2}"

        self.when_dict = {
            "S": "%Y-%m-%d-%H-%M-%S",
            "M": "%Y-%m-%d-%H-%M",
            "H": "%Y-%m-%d-%H",
            "D": "%Y-%m-%d",
        }

        self.suffix = self.when_dict.get(when)
        if not self.suffix:
            print("The specified date interval unit is invalid: ", self.when)
            sys.exit(1)

        self.filefmt = os.path.join(".", "logs", f"{self.prefix}-{self.suffix}.log")

        self.filePath = datetime.datetime.now().strftime(self.filefmt)

        _dir = os.path.dirname(self.filefmt)
        try:
            if not os.path.exists(_dir):
                os.makedirs(_dir)
        except Exception as e:
            print("Failed to create log file: ", e)
            print("log_path：" + self.filePath)
            sys.exit(1)

        logging.FileHandler.__init__(self, self.filePath, "a+", encoding, delay)

    def shouldChangeFileToWrite(self):
        _filePath = datetime.datetime.now().strftime(self.filefmt)
        if _filePath != self.filePath:
            self.filePath = _filePath
            return True
        return False

    def doChangeFile(self):
        self.baseFilename = os.path.abspath(self.filePath)
        if self.stream:
            self.stream.close()
            self.stream = None

        if not self.delay:
            self.stream = self._open()
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)

    def getFilesToDelete(self):
        dir_name, _ = os.path.split(self.baseFilename)
        file_names = os.listdir(dir_name)
        result = []
        prefix = self.prefix + "-"
        for file_name in file_names:
            if file_name[: len(prefix)] == prefix:
                suffix = file_name[len(prefix): -4]
                if re.compile(self.extMath).match(suffix):
                    result.append(os.path.join(dir_name, file_name))
        result.sort()

        if len(result) < self.backupCount:
            result = []
        else:
            result = result[: len(result) - self.backupCount]
        return result

    def emit(self, record):
        try:
            if self.shouldChangeFileToWrite():
                self.doChangeFile()
            logging.FileHandler.emit(self, record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


def write_log(log_name, log_num=7):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s ｜ %(levelname)s ｜ %(filename)s ｜ %(funcName)s ｜ %(lineno)s ｜ %(message)s"
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(fmt)

    file_handler = MultiprocessHandler(log_name, when="D", backupCount=log_num, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(fmt)
    file_handler.doChangeFile()

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger


# 为zhiwang.py创建专用的日志记录器
def create_zhiwang_logger(log_name = project_name):
    logger = logging.getLogger("zhiwang")
    logger.setLevel(logging.INFO)

    # 避免重复添加处理器
    if not logger.handlers:
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 设置日志格式
        formatter = logging.Formatter(
            "%(asctime)s｜%(levelname)s｜%(filename)s｜%(funcName)s｜%(lineno)s｜%(message)s"
        )
        console_handler.setFormatter(formatter)
        file_handler = MultiprocessHandler(log_name, when="D", backupCount=7, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        file_handler.doChangeFile()
        # 添加处理器到日志记录器
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger




# LOGGER = write_log(log_name=project_name)
