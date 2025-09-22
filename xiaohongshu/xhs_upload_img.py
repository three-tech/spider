import base64
import os
import time
from pathlib import Path

from playwright.async_api import async_playwright

from base.database import MemberXhs
from conf import LOCAL_CHROME_PATH, BASE_DIR
from utils.base_social_media import set_init_script
from utils.log import xiaohongshu_logger

open_url = "https://creator.xiaohongshu.com/publish/publish?source=official"
xhs_cookie_path = Path(BASE_DIR / "cookies" / "xiaohongshu")


class XiaoHongShuImg(object):

    def __init__(self, user_name, title, file_path, tags, publish_date, member_xhs: MemberXhs, content=None,
                 headless=False):
        # 初始化笔记标题
        self.title = self._remove_links(title)
        # 初始化笔记内容
        self.content = self._remove_links(content or "")
        # 处理文件路径，将逗号分隔的路径转换为列表
        self.file_path = file_path.split(',')
        # 初始化标签列表
        self.tags = tags
        # 设置发布日期
        self.publish_date = publish_date
        # 设置cookie文件路径
        self.cookie_file = Path(xhs_cookie_path, f"cookie-{user_name}.json")
        # 定义日期格式
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.headless = headless
        self.user_name = user_name
        self.qr_path = f"{xhs_cookie_path}/{self.user_name}-qrcode.png"
        self.member_xhs = member_xhs
        self.local_executable_path = LOCAL_CHROME_PATH

    async def cookie_auth(self):
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=self.cookie_file)
            context = await set_init_script(context)
            # 创建一个新的页面
            page = await context.new_page()
            # 访问指定的 URL
            await page.goto("https://creator.xiaohongshu.com/creator-micro/content/upload")
            try:
                await page.wait_for_url("https://creator.xiaohongshu.com/creator-micro/content/upload", timeout=5000)
            except:
                print("[+] 等待5秒 cookie 失效")
                await context.close()
                await browser.close()
                return False
            if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
                print("[+] 等待5秒 cookie 失效")
                return False
            else:
                print("[+] cookie 有效")
                return True

    async def setup(self):
        if not os.path.exists(self.cookie_file) or not await self.cookie_auth():
            xiaohongshu_logger.info(
                '[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
            await self.gen_cookie()
        return True

    async def gen_cookie(self):
        # 确保account_file的目录存在，如果不存在则创建
        account_dir = os.path.dirname(self.cookie_file)
        if account_dir and not os.path.exists(account_dir):
            os.makedirs(account_dir)
            print(f"[+] 创建目录: {account_dir}")

        async with async_playwright() as playwright:
            options = {
                'headless': False
            }
            # Make sure to run headed.
            browser = await playwright.chromium.launch(**options)
            # Setup context however you like.
            context = await browser.new_context()  # Pass any options
            context = await set_init_script(context)
            # Pause the page, and start recording manually.
            page = await context.new_page()
            await page.goto("https://creator.xiaohongshu.com/")
            # 下载二维码
            await self.download_qr(page)
            await page.pause()
            # 点击调试器的继续，保存cookie
            await context.storage_state(path=self.cookie_file)

    async def download_qr(self, page):
        await page.locator("img").click()
        # 等待图片元素出现
        # await page.wait_for_selector("img:nth(2)")
        # 获取图片元素
        img_element = page.get_by_role("img").nth(2)
        # 获取图片的src属性
        img_src = await img_element.get_attribute("src")
        # 假设 img_src 是你从页面获取的 base64 字符串
        # 去除 base64 字符串的前缀（如 "data:image/png;base64,"）
        base64_data = img_src.split(",")[1]
        # 解码 base64 数据
        img_data = base64.b64decode(base64_data)
        # 保存图片到本地
        with open(self.qr_path, "wb") as f:
            f.write(img_data)
        print(f"[+] 二维码图片已保存为 {self.qr_path}")

    async def main(self):
        # 设置 Cookie
        await self.setup()
        xiaohongshu_logger.info(f'[-] {self.user_name} 获取Cookie成功...')
        # 执行上传
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def upload(self, playwright):
        browser = await playwright.chromium.launch(executable_path=self.local_executable_path, headless=self.headless)
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(
            viewport={"width": 1440, "height": 700},
            storage_state=f"{self.cookie_file}"
        )
        # context = await set_init_script(context)

        # 创建一个新的页面
        page = await context.new_page()
        # 等待页面加载完成
        await page.goto(open_url)
        await page.wait_for_url(open_url)
        xiaohongshu_logger.info(f'[-] 正在打开首页...')

        # 等待页面加载完成，确保元素出现
        await page.wait_for_selector('div.header div.creator-tab', timeout=30000)
        await page.get_by_text("上传图文").nth(1).click()
        xiaohongshu_logger.info(f'[-] 跳转到图文上传页面...')
        # await page.pause()
        # await page.get_by_role("button", name="Choose File").click()
        await page.get_by_role("button", name="Choose File").set_input_files(self.file_path)
        await page.get_by_role("textbox", name="填写标题会有更多赞哦～").click()
        await page.get_by_role("textbox", name="填写标题会有更多赞哦～").fill(self.title)
        await page.get_by_role("textbox").nth(1).click()
        content = f"""
        {self.content}
        {self.member_xhs.topic}
        """
        await page.get_by_role("textbox").nth(1).fill(content)

        # 保持页面打开一段时间以便观察
        time.sleep(600)

    def _remove_links(self, text):
        """
        清除文本中的超链接
        Args:
            text: 输入文本
        Returns:
            清除超链接后的文本
        """
        if not text:
            return text
            
        import re
        # 移除URL链接
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除Markdown链接
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        return text.strip()
