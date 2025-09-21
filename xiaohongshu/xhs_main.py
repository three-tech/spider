import asyncio

from xiaohongshu.xhs_upload_img import XiaoHongShuImg

file_path = '/Users/xuzongxin/Downloads/WechatIMG218.jpg,/Users/xuzongxin/Downloads/WechatIMG218.jpg'


async def main():
    xhs = XiaoHongShuImg('测试账号', 'test', file_path, 'test', '2022-03-01 00:00:00')
    await xhs.main()


if __name__ == '__main__':
    asyncio.run(main())
