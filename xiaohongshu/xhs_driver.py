from playwright.async_api import async_playwright, BrowserContext


async def start_chrome_with_debugging(port=9222, user_data_dir=None):
    """
    使用Playwright启动带有远程调试功能的Chrome浏览器
    
    Args:
        port: 调试端口，默认为9222
        user_data_dir: 用户数据目录，如果为None则使用默认目录
        
    Returns:
        None
    """
    try:
        playwright = await async_playwright().start()

        # Chrome启动参数
        chrome_args = [
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
        ]

        # 如果指定了用户数据目录，则添加该参数
        if user_data_dir:
            chrome_args.append(f"--user-data-dir={user_data_dir}")

        # 启动Chrome浏览器
        browser = await playwright.chromium.launch(
            headless=False,
            args=chrome_args
        )

        print(f"Chrome started with debugging on port {port}")
        return browser
    except Exception as e:
        print(f"Failed to start Chrome: {e}")
        raise


async def attach_to_existing_chrome(remote_debugging_port=9222) -> BrowserContext:
    """
    连接到已经打开的Chrome浏览器窗口

    使用方法：
    1. 先启动Chrome浏览器时添加参数 --remote-debugging-port=9222
       或者调用 start_chrome_with_debugging() 函数
    2. 然后调用此函数连接到该浏览器实例

    Args:
        remote_debugging_port: Chrome远程调试端口，默认为9222

    Returns:
        BrowserContext实例
    """
    playwright = await async_playwright().start()

    try:
        # 连接到现有的Chrome浏览器
        browser = await playwright.chromium.connect_over_cdp(
            f"http://localhost:{remote_debugging_port}"
        )

        # 获取默认的浏览器上下文
        context = browser.contexts[0] if browser.contexts else await browser.new_context()

        print(f"Successfully connected to Chrome on port {remote_debugging_port}")
        return context
    except Exception as e:
        print(f"Failed to connect to Chrome: {e}")
        print("Make sure Chrome is running with --remote-debugging-port={}".format(remote_debugging_port))
        raise
