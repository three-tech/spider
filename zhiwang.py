# -*- coding: utf-8 -*-
import csv
import os
import re
import time  # 模拟人类休眠用
from difflib import SequenceMatcher

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By  # 找元素时用
from tornado import concurrent

from driver import init_chrome_driver
from utils.logs import create_zhiwang_logger

logger = create_zhiwang_logger('spider')

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PATH_ZHIWANG = os.path.join(PROJECT_ROOT, 'data', 'zhiwang.csv')
PATH_KEYS = os.path.join(PROJECT_ROOT, 'data', 'keys.txt')
PATH_KEYS_NOT = os.path.join(PROJECT_ROOT, 'data', 'keys_not.txt')
PATH_ZHIWANG_DETAIL = os.path.join(PROJECT_ROOT, 'data', 'zhiwang')
PATH_ZHIWANG_NEW = os.path.join(PROJECT_ROOT, 'data', 'zhiwang_new.csv')
PATH_ZHIWANG_SOURCE = os.path.join(PROJECT_ROOT, 'data', 'html')
pattern = r'\((.*?)\)'

suf = "/" + time.strftime("%Y%m%d%H%M%S", time.localtime()) + ".csv"


# 找到输入框，输入岗位名称

class ZhiWang:
    total_cnt = 0
    success_cnt = 0

    def __init__(self):
        self.query_key = ""
        self.data_year = ""
        self.publish_date = ""
        self.publish_org_list = ""
        self.author_list = ""
        self.title = ""
        self.source_journal = ""
        self.journal_no = ""
        self.class_no = ""
        self.page_no = ""
        self.data_source_link = ""

    def fromDict(self, dict_data: dict[str, str]):
        self.query_key = dict_data.get("查询关键字")
        self.data_year = dict_data.get("数据年份")
        self.publish_date = dict_data.get("发表日期")
        self.publish_org_list = dict_data.get("全部单位名称")
        self.author_list = dict_data.get("作者名称")
        self.title = dict_data.get("论文名称")
        self.source_journal = dict_data.get("来源期刊")
        self.journal_no = dict_data.get("刊次")
        self.class_no = dict_data.get("分类号")
        self.page_no = dict_data.get("页码")
        self.data_source_link = dict_data.get("链接")
        return self

    def toDict(self) -> dict:
        return {
            "查询关键字": self.query_key,
            "数据年份": self.data_year,
            "发表日期": self.publish_date,
            "全部单位名称": self.publish_org_list,
            "作者名称": self.author_list,
            "论文名称": self.title,
            "来源期刊": self.source_journal,
            "刊次": self.journal_no,
            "分类号": self.class_no,
            "页码": self.page_no,
            "链接": self.data_source_link
        }

    def addToCsv(self, path):
        if self.data_source_link == "":
            return
        logger.info(self.toDict())
        ZhiWang.success_cnt += 1
        # 将字典追加写入CSV文件
        file_exists = os.path.isfile(path)
        with open(path, mode='a', encoding='utf-8-sig', newline='') as csvfile:
            fieldnames = ["查询关键字", "数据年份", "发表日期", "全部单位名称", "作者名称", "论文名称", "来源期刊",
                          "刊次", "分类号",
                          "页码", "链接"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # 如果文件不存在，写入表头
            if not file_exists:
                writer.writeheader()

            # 写入当前记录
            writer.writerow(self.toDict())


def parse_single_key(key):
    driver = init_chrome_driver(False)
    # 进入官网
    driver.get("https://kns.cnki.net/kns8s/search?")

    # 让子弹飞一会儿，让网页加载一会儿
    time.sleep(5)
    driver.find_element(By.XPATH, '//input[@id="txt_search"]').send_keys(key)
    # 模拟人类，等待5秒
    time.sleep(5)
    # 点击查找按钮
    driver.find_element(By.XPATH,
                        '//div[@id="ModuleSearch"]/div[1]/div[@class="search-box"]/div[@class="content"]/div[@class="search-main"]/div[@class="input-box"]/input[@class="search-btn"]').click()
    # 一个比较长的加载过程
    time.sleep(5)

    if save_not_exist_data(driver, key):
        logger.info(f"{key} 明确不存在")
        return

    # 使用XPath查找表格元素，然后获取其行数来判断列表数量
    table_rows = driver.find_elements(By.XPATH,
                                      "//div[@id='gridTable']/div/div/div/table[@class='result-table-list']//tr")
    list_count = len(table_rows) - 1  # 减去表头行
    logger.info(f"{key}  列表数量: {list_count}")
    if list_count < 0:
        zw = ZhiWang()
        zw.query_key = key
        zw.addToCsv(PATH_ZHIWANG_DETAIL)
        return

    # 计算标题与查询关键字的相似度并排序

    similarity_list = []
    for tr in table_rows[1:]:  # 跳过表头行
        try:
            name_element = tr.find_element(By.XPATH, "./td[@class='name']")
            title = name_element.text.strip()
            # 计算相似度
            similarity = SequenceMatcher(None, key, title).ratio()
            similarity_list.append((similarity, tr))
        except Exception as e:
            logger.info(f"计算相似度时出错: {e}")

    # 按相似度降序排序
    # 按相似度降序排序，确保最相似的标题排在前面
    similarity_list.sort(key=lambda x: x[0], reverse=True)
    tr = similarity_list[0][1]
    zw = ZhiWang()
    zw.query_key = key
    try:
        name_element = tr.find_element(By.XPATH, "./td[@class='name']")
        zw.title = name_element.text.strip()
        zw.data_source_link = name_element.find_element(By.TAG_NAME, 'a').get_attribute('href')
        zw.author_list = tr.find_element(By.XPATH, "./td[@class='author']").text.strip()
        # 处理跳转
        pase_link(zw, driver, name_element)
    except Exception as e:
        logger.info(f"{zw.data_source_link} 解析失败: {e}")
    driver.quit()


def save_not_exist_data(driver, key) -> bool:
    v = '抱歉，暂无数据，请稍后重试。'
    if v in driver.page_source:
        with open(PATH_KEYS_NOT, 'a', encoding='utf-8') as f:
            f.write(key + '\n')
        return True
    return False


def pase_link(d: ZhiWang, driver, name_element):
    link = d.data_source_link
    if pd.isna(link):
        d.addToCsv(PATH_ZHIWANG_DETAIL)
        return
    link_element = name_element.find_element(By.TAG_NAME, 'a')
    # 点击链接
    link_element.click()
    # 等待页面加载
    time.sleep(5)
    # 获取当前窗口句柄
    original_window = driver.current_window_handle
    # 切换到新打开的标签页（如果有的话）
    for window_handle in driver.window_handles:
        if window_handle != original_window:
            driver.switch_to.window(window_handle)
            break
    logger.info(f'处理：{d.title}  {d.data_source_link}')
    # 保存原网页
    # save_source(driver, d)
    # 分析
    analyze_by_soup(driver.page_source, d)
    # 保存
    d.addToCsv(PATH_ZHIWANG_DETAIL)


def save_source(driver, d: ZhiWang):
    # 保存当前页面的HTML到本地文件
    page_html = driver.page_source
    filename = f"{d.title.replace('/', '_')}.html"  # 处理非法字符
    filepath = os.path.join(PATH_ZHIWANG_SOURCE, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)  # 确保目录存在
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(page_html)
    logger.info(f"已保存HTML到: {filepath}")


def analyze_by_soup(content, zw: ZhiWang):
    try:
        soup = BeautifulSoup(content, 'html.parser')
        zw.source_journal, zw.data_year, zw.journal_no = get_top_data(soup, zw.query_key)
        zw.page_no = get_page_no(soup, zw.query_key)
        zw.publish_org_list = get_pub_org(soup, zw.query_key)
        zw.publish_date = get_pub_date(soup, zw.query_key)
        zw.class_no = get_class_no(soup, zw.query_key)
    except Exception as e:
        logger.info(f"解析HTML出错: {zw.data_source_link}  {e}")


def get_top_data(soup: BeautifulSoup, key: str):
    try:
        tops = soup.select_one('div.top-tip').find_all('a')
        if tops and len(tops) > 1:
            source_journal = tops[0].text.strip().replace('.', '')
            year_and_no = tops[1].text.replace(' ', '').replace('\n', '')
            data_year = year_and_no[0:4]
            match = re.search(pattern, year_and_no)
            if match:
                journal_no = 'No.' + match.group(1)
            else:
                journal_no = data_year[4:]
            return source_journal, data_year, journal_no
        else:
            return "未知", "未知", "未知"
    except  Exception as e:
        logger.info(f"解析top数据时出错: {key} {e}")
        return "未知", "未知", "未知"


def get_page_no(soup: BeautifulSoup, key: str):
    try:
        page_no_element = soup.select_one('span:-soup-contains("页码")')
        if page_no_element:
            page_no_text = page_no_element.text
            if '：' in page_no_text:
                page_no = page_no_text.split('：')[1]
            else:
                page_no = '未披露'
        else:
            page_no = '未披露'
        return f'[{page_no}]'
    except Exception as e:
        logger.info(f"页码查找异常: {key} {e}")
        return '未披露'


def get_class_no(soup: BeautifulSoup, key: str):
    try:
        class_no_element = soup.select_one('span:-soup-contains("分类号")')
        if class_no_element:
            class_no = class_no_element.find_next_sibling('p', class_='clc-code')
            if class_no:
                class_no = class_no.text
            else:
                class_no = "未披露"
        else:
            class_no = "未披露"
        return class_no
    except Exception as e:
        logger.info(f"获取分类号异常: {key} {e}")
        return '未披露'


def get_pub_date(soup: BeautifulSoup, key: str):
    try:
        open_time = soup.select_one('span:-soup-contains("在线公开时间")')
        if open_time:
            open_time = open_time.find_next_sibling('p')
            if open_time:
                open_time = open_time.text.split("（")[0].split(" ")[0].replace("-", ".")
            else:
                open_time = "未披露"
        else:
            open_time = "未披露"
        return open_time
    except Exception as e:
        logger.info(f"获取分类号异常: {key} {e}")
        return '未披露'


def get_pub_org(soup: BeautifulSoup, key: str):
    try:
        publish_org_list_elem = soup.select_one(
            "body > div.wrapper > div.main > div.container > div > div:nth-child(3) > div.brief > div > h3:nth-child(3)")
        if publish_org_list_elem:
            return publish_org_list_elem.get_text().strip().replace('                      ', ';').replace(' ', '')
        else:
            return ""
    except Exception as e:
        logger.info(f"未能找到全部单位名称元素:{key} {e}")
        return ""


def analyze():
    mf = pd.read_csv(PATH_ZHIWANG_DETAIL)

    # 遍历DataFrame，检查'全部单位名称'列是否包含'1.'
    for index, row in mf.iterrows():
        # 过滤论文名称不为空的
        if pd.isna(row['论文名称']) or row['论文名称'].strip() == '':
            continue

        html_filename = f"{row['论文名称'].replace('/', '_')}.html"
        html_filepath = os.path.join(PATH_ZHIWANG_SOURCE, html_filename)

        # 检查HTML文件是否存在
        if os.path.exists(html_filepath):
            # 使用BeautifulSoup加载并解析本地HTML文件
            with open(html_filepath, 'r', encoding='utf-8') as f:
                z = ZhiWang()
                z.fromDict(row.to_dict())
                analyze_by_soup(f.read(), z)
                z.addToCsv(PATH_ZHIWANG_NEW)


def run(work_cnt=1, enable_filter=True, start_key=''):
    # 读取配置
    with open(PATH_KEYS, 'r', encoding='utf-8') as f:
        keysList = [line.strip() for line in f.readlines()]
    # 读取明确不存在的
    create_file(PATH_KEYS_NOT)
    with open(PATH_KEYS_NOT, 'r', encoding='utf-8') as f:
        keysNotList = [line.strip() for line in f.readlines()]
    keysList = [key for key in keysList if key not in keysNotList]

    # 遗漏过滤
    if enable_filter and os.path.exists(PATH_ZHIWANG_DETAIL):
        df = pd.read_csv(PATH_ZHIWANG_DETAIL)
        keysList = [key for key in keysList if key not in df['查询关键字'].tolist()]

    # 截取列表
    if start_key and start_key in keysList:
        keysList = keysList[keysList.index(start_key):]
    ZhiWang.total_cnt = len(keysList)
    logger.info(f"待处理列表: {ZhiWang.total_cnt}\n {keysList}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=work_cnt) as executor:
        # 提交任务到线程池
        futures = [executor.submit(parse_single_key, key) for key in keysList]
        # 每30秒输出一次剩余任务量
        while any(not future.done() for future in futures):
            remaining = sum(1 for future in futures if not future.done())
            logger.info(f"剩余任务量: {remaining}")
            time.sleep(30)
        # 等待所有任务完成
        concurrent.futures.wait(futures)
    logger.info(f"总数量: {ZhiWang.total_cnt} 成功数量: {ZhiWang.success_cnt}")


def create_file(path):
    if not os.path.exists(path):
        open(path, 'w', encoding='utf-8').close()  # 创建空文件


if __name__ == '__main__':
    suf = '/zhiwang-3.csv'
    PATH_ZHIWANG_DETAIL += suf
    # analyze()
    run(5, True, '')
