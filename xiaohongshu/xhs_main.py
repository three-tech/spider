import asyncio
import time
from pathlib import Path

from conf import BASE_DIR
from xiaohongshu.xhs_upload_img import XiaoHongShuImg

cookie_file = Path(BASE_DIR / "cookies" / "xiaohongshu_uploader" / "58a391ba-4082-11f0-a321-44e51723d63c.json")


async def main():
    xhs = XiaoHongShuImg('test', '/Users/xuzongxin/Downloads/WechatIMG218.jpg', 'test', '2022-03-01 00:00:00',
                         cookie_file)
    await xhs.main()


if __name__ == '__main__':
    asyncio.run(main())
