import time

from playwright.async_api import async_playwright

from conf import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.log import xiaohongshu_logger
from xiaohongshu.xhs_cookie import xiaohongshu_setup

open_url = "https://creator.xiaohongshu.com/publish/publish?source=official"


class XiaoHongShuImg(object):

    def __init__(self, title, file_path, tags, publish_date, cookie_file, headless=False):
        # 初始化笔记标题
        self.title = title
        # 处理文件路径，将逗号分隔的路径转换为列表
        self.file_path = file_path.split(',')
        # 初始化标签列表
        self.tags = tags
        # 设置发布日期
        self.publish_date = publish_date
        # 设置cookie文件路径
        self.cookie_file = cookie_file
        # 定义日期格式
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.headless = headless
        self.local_executable_path = LOCAL_CHROME_PATH

    async def main(self):
        # 设置 Cookie
        await xiaohongshu_setup(self.cookie_file)
        # 执行上传
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def upload(self, playwright):
        browser = await playwright.chromium.launch(executable_path=self.local_executable_path, headless=self.headless)
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(
            viewport={"width": 1440, "height": 800},
            storage_state=f"{self.cookie_file}"
        )
        context = await set_init_script(context)

        # 创建一个新的页面
        page = await context.new_page()
        # 等待页面加载完成
        await page.wait_for_url(open_url)
        xiaohongshu_logger.info(f'[-] 正在打开首页...')

        # 点击上传图文按钮
        await page.click('span.title:has-text("上传图文")')
        xiaohongshu_logger.info('[+] 已进入图文发布页面')

        # 保持页面打开一段时间以便观察
        time.sleep(60)
