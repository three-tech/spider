"""
基础工具函数模块
"""

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import requests


def ensure_dir(path: Union[str, Path]) -> None:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def read_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    读取JSON文件
    
    Args:
        file_path: JSON文件路径
        
    Returns:
        JSON数据字典
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取JSON文件失败 {file_path}: {e}")
        return {}


def write_json(data: Dict[str, Any], file_path: Union[str, Path], indent: int = 2) -> bool:
    """
    写入JSON文件
    
    Args:
        data: 要写入的数据
        file_path: JSON文件路径
        indent: 缩进空格数
        
    Returns:
        是否写入成功
    """
    try:
        ensure_dir(os.path.dirname(file_path))
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        return True
    except Exception as e:
        print(f"写入JSON文件失败 {file_path}: {e}")
        return False


def get_timestamp() -> int:
    """
    获取当前时间戳（秒）
    
    Returns:
        时间戳
    """
    return int(time.time())


def get_datetime_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    获取当前时间字符串
    
    Args:
        fmt: 时间格式
        
    Returns:
        时间字符串
    """
    return datetime.now().strftime(fmt)


def parse_datetime(date_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """
    解析时间字符串
    
    Args:
        date_str: 时间字符串
        fmt: 时间格式
        
    Returns:
        datetime对象，解析失败返回None
    """
    try:
        return datetime.strptime(date_str, fmt)
    except ValueError:
        return None


def get_md5(text: str) -> str:
    """
    获取字符串的MD5哈希值
    
    Args:
        text: 输入字符串
        
    Returns:
        MD5哈希值
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    获取文件大小（字节）
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件大小，文件不存在返回0
    """
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def format_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 字节数
        
    Returns:
        格式化后的大小字符串
    """
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f}{size_names[i]}"


def safe_filename(filename: str) -> str:
    """
    生成安全的文件名，移除或替换不安全字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        安全的文件名
    """
    # 移除或替换不安全字符
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')

    # 移除首尾空格和点号
    filename = filename.strip(' .')

    # 限制长度
    if len(filename) > 200:
        filename = filename[:200]

    return filename or 'unnamed'


def retry_on_exception(max_retries: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
        exceptions: 需要重试的异常类型
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        print(f"函数 {func.__name__} 第 {attempt + 1} 次执行失败: {e}")
                        print(f"等待 {delay} 秒后重试...")
                        time.sleep(delay)
                    else:
                        print(f"函数 {func.__name__} 重试 {max_retries} 次后仍然失败")

            raise last_exception

        return wrapper

    return decorator


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    将列表分块
    
    Args:
        lst: 输入列表
        chunk_size: 每块大小
        
    Returns:
        分块后的列表
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    扁平化嵌套字典
    
    Args:
        d: 嵌套字典
        parent_key: 父键名
        sep: 分隔符
        
    Returns:
        扁平化后的字典
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def is_valid_url(url: str) -> bool:
    """
    检查URL是否有效
    
    Args:
        url: URL字符串
        
    Returns:
        是否有效
    """
    import re
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return pattern.match(url) is not None


def download_image(url: str, save_dir: Optional[str] = None, timeout: int = 30) -> Optional[str]:
    """
    下载图片到本地
    
    Args:
        url: 图片URL
        save_dir: 保存目录，如果为None则使用临时目录
        timeout: 超时时间（秒）
        
    Returns:
        本地文件路径，下载失败返回None
    """
    try:
        if not is_valid_url(url):
            print(f"无效的URL: {url}")
            return None

        # 解析URL获取文件名
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)

        # 如果没有文件扩展名，尝试从URL推断
        if not filename or '.' not in filename:
            # 生成基于URL哈希的文件名
            url_hash = get_md5(url)[:8]
            filename = f"image_{url_hash}.jpg"

        # 确保文件名安全
        filename = safe_filename(filename)

        # 确定保存路径
        if save_dir is None:
            save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'tmp')
        else:
            ensure_dir(save_dir)

        file_path = os.path.join(save_dir, filename)

        # 下载图片
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()

        # 检查内容类型
        content_type = response.headers.get('content-type', '').lower()
        if not content_type.startswith('image/'):
            print(f"URL不是图片类型: {url}, content-type: {content_type}")
            return None

        # 保存文件
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        print(f"图片下载成功: {url} -> {file_path}")
        return file_path

    except Exception as e:
        print(f"下载图片失败 {url}: {e}")
        return None


def download_images(urls: List[str], save_dir: Optional[str] = None, max_images: int = 9) -> List[str]:
    """
    批量下载图片
    
    Args:
        urls: 图片URL列表
        save_dir: 保存目录
        max_images: 最大下载数量
        
    Returns:
        成功下载的本地文件路径列表
    """
    if not urls:
        return []

    # 限制下载数量
    urls = urls[:max_images]

    downloaded_paths = []

    for i, url in enumerate(urls):
        print(f"正在下载第 {i + 1}/{len(urls)} 张图片...")
        file_path = download_image(url, save_dir)
        if file_path:
            downloaded_paths.append(file_path)
        else:
            print(f"跳过无效图片: {url}")

    print(f"批量下载完成: {len(downloaded_paths)}/{len(urls)} 张图片成功")
    return downloaded_paths


def cleanup_files(file_paths: List[str]) -> int:
    """
    清理文件列表
    
    Args:
        file_paths: 要删除的文件路径列表
        
    Returns:
        成功删除的文件数量
    """
    deleted_count = 0

    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"已删除文件: {file_path}")
                deleted_count += 1
            else:
                print(f"文件不存在，跳过删除: {file_path}")
        except Exception as e:
            print(f"删除文件失败 {file_path}: {e}")

    print(f"文件清理完成: 删除了 {deleted_count}/{len(file_paths)} 个文件")
    return deleted_count


class ImageDownloadManager:
    """
    图片下载管理器
    提供完整的下载-使用-清理流程
    """

    def __init__(self, save_dir: Optional[str] = None):
        """
        初始化图片下载管理器
        
        Args:
            save_dir: 保存目录，如果为None则使用临时目录
        """
        if save_dir is None:
            self.save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'tmp')
        else:
            self.save_dir = save_dir

        ensure_dir(self.save_dir)
        self.downloaded_files = []

    def download_images(self, urls: List[str], max_images: int = 9) -> List[str]:
        """
        下载图片列表
        
        Args:
            urls: 图片URL列表
            max_images: 最大下载数量
            
        Returns:
            本地文件路径列表
        """
        downloaded_paths = download_images(urls, self.save_dir, max_images)
        self.downloaded_files.extend(downloaded_paths)
        return downloaded_paths

    def cleanup(self) -> int:
        """
        清理所有下载的文件
        
        Returns:
            删除的文件数量
        """
        deleted_count = cleanup_files(self.downloaded_files)
        self.downloaded_files.clear()
        return deleted_count

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口，自动清理文件"""
        self.cleanup()
