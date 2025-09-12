from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def init_chrome_driver(headless=True):
    chrome_options = webdriver.ChromeOptions()
    # 关键：禁用自动化检测（规避知网对WebDriver的识别）
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    # 无头模式会触发更严格的反爬，建议先开启可视化模式调试
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    # 伪装正常浏览器的User-Agent（避免被识别为爬虫）
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    # chrome_options.add_argument("--proxy-server=http://127.0.0.1:7890")


    # 初始化驱动（自动安装匹配的ChromeDriver）
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    # 进一步规避反爬：删除navigator.webdriver标记
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        }
    )
    return driver
