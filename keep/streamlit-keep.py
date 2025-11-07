import os
import time
import datetime
import pytz  # pip install pytz
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StreamlitAppWaker:
    """
    针对Streamlit应用的自动唤醒脚本
    """
    APP_URL = os.environ.get("STREAMLIT_APP_URL", "https://python-xray-argo-h6vbhnptbecuyjjyhtuaqr.streamlit.app")
    INITIAL_WAIT_TIME = 10
    POST_CLICK_WAIT_TIME = 20
    BUTTON_TEXT = "Yes, get this app back up!"
    BUTTON_SELECTOR = "//button[text()='Yes, get this app back up!']"

    def __init__(self):
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        logger.info("⚙️ 正在设置Chrome驱动...")
        chrome_options = Options()

        if os.getenv('GITHUB_ACTIONS'):
            logger.info("⚙️ 检测到CI环境，启用headless模式。")
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')

        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("✅ Chrome驱动设置完成。")
        except Exception as e:
            logger.error(f"❌ 驱动初始化失败: {e}")
            raise

    def wait_for_element_clickable(self, by, value, timeout=10):
        return WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((by, value)))
    
    def find_and_click_button(self, context_description="主页面"):
        logger.info(f"🔍 尝试在 {context_description} 查找唤醒按钮: '{self.BUTTON_TEXT}'")
        try:
            button = self.wait_for_element_clickable(By.XPATH, self.BUTTON_SELECTOR, 5)
            if button.is_displayed() and button.is_enabled():
                button.click()
                logger.info(f"✅ 在 {context_description} 成功点击唤醒按钮。")
                return True
            else:
                logger.warning(f"⚠️ 在 {context_description} 找到按钮，但按钮不可点击或不可见。")
                return False
        except TimeoutException:
            logger.info(f"❌ 在 {context_description} 规定时间内未找到唤醒按钮。")
            return False
        except Exception as e:
            logger.error(f"❌ 在 {context_description} 点击按钮时发生异常: {e}")
            return False

    def is_app_woken_up(self):
        logger.info("🧐 检查唤醒按钮是否已消失...")
        self.driver.switch_to.default_content()
        try:
            WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, self.BUTTON_SELECTOR)))
            logger.info("❌ 唤醒按钮仍在主页面显示。")
            return False
        except TimeoutException:
            logger.info("✅ 唤醒按钮在主页面已消失。")

        try:
            iframe = self.driver.find_element(By.TAG_NAME, "iframe")
            self.driver.switch_to.frame(iframe)
            WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, self.BUTTON_SELECTOR)))
            self.driver.switch_to.default_content()
            logger.info("❌ 唤醒按钮在 iframe 内仍显示。")
            return False
        except (NoSuchElementException, TimeoutException):
            self.driver.switch_to.default_content()
            logger.info("✅ 应用唤醒成功。")
            return True
        except Exception as e:
            self.driver.switch_to.default_content()
            logger.error(f"❌ 检查唤醒状态时发生异常: {e}")
            return False

    def wakeup_app(self):
        if not self.APP_URL:
            raise Exception("⚠️ STREAMLIT_APP_URL 未配置。")
        logger.info(f"👉 访问应用URL: {self.APP_URL}")
        self.driver.get(self.APP_URL)
        logger.info(f"⏳ 等待初始页面加载 {self.INITIAL_WAIT_TIME} 秒...")
        time.sleep(self.INITIAL_WAIT_TIME)

        click_success = self.find_and_click_button("主页面")

        if not click_success:
            logger.info("👉 主页面未找到按钮，尝试进入 iframe...")
            try:
                iframe = self.driver.find_element(By.TAG_NAME, "iframe")
                self.driver.switch_to.frame(iframe)
                click_success = self.find_and_click_button("iframe内部")
                self.driver.switch_to.default_content()
            except Exception as e:
                logger.error(f"❌ iframe 查找失败: {e}")

        if not click_success:
            if self.is_app_woken_up():
                return True, "✅ 应用已处于唤醒状态。"
            else:
                raise Exception("⚠️ 未找到或无法点击唤醒按钮。")

        logger.info(f"⏳ 成功点击唤醒按钮，等待 {self.POST_CLICK_WAIT_TIME} 秒...")
        time.sleep(self.POST_CLICK_WAIT_TIME)

        if self.is_app_woken_up():
            return True, "✅ 应用唤醒成功！"
        else:
            raise Exception("❌ 唤醒按钮仍存在，应用可能未能启动。")

    def run(self):
        try:
            logger.info("🚀 开始执行唤醒流程...")
            success, result = self.wakeup_app()
            return success, result
        except Exception as e:
            return False, f"❌ 执行失败: {e}"
        finally:
            if self.driver:
                logger.info("🧹 关闭Chrome驱动...")
                self.driver.quit()

# ✅ 新增的部分（每天定时运行）
def main():
    app_url = os.environ.get("STREAMLIT_APP_URL", "https://python-xray-argo-h6vbhnptbecuyjjyhtuaqr.streamlit.app")
    logger.info(f"配置的应用 URL: {app_url}")
    waker = StreamlitAppWaker()
    success, result = waker.run()
    logger.info(result)

def run_daily_at_midnight():
    tz = pytz.timezone("Asia/Shanghai")
    logger.info("🕓 启动定时任务：每天北京时间 00:00 自动执行唤醒脚本。")
    while True:
        now = datetime.datetime.now(tz)
        next_run = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_seconds = (next_run - now).total_seconds()
        logger.info(f"⏳ 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}，下次运行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(wait_seconds)
        logger.info("🚀 到达执行时间，开始唤醒 Streamlit 应用。")
        main()

if __name__ == "__main__":
    run_daily_at_midnight()
