# -*- coding: utf-8 -*-
"""
browser.py — Selenium Edge 브라우저 래퍼

사용법:
  with Browser(headless=True) as b:
      b.goto("https://ads.naver.com")
      b.click("button.login")
      b.type("input#id", "my_id")
      html = b.html()

헤드리스 모드(headless=True)가 기본값.
로그인 등 사람 확인이 필요한 경우 headless=False 사용.
"""
import os
import time
from pathlib import Path
from typing import Optional

DEFAULT_DOWNLOAD_DIR = str(Path("output/downloads").resolve())


class Browser:
    def __init__(self, headless: bool = True, download_dir: Optional[str] = None):
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
        from selenium.webdriver.edge.service import Service
        from webdriver_manager.microsoft import EdgeChromiumDriverManager

        self._download_dir = download_dir or DEFAULT_DOWNLOAD_DIR
        Path(self._download_dir).mkdir(parents=True, exist_ok=True)

        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("prefs", {
            "download.default_directory":     self._download_dir,
            "download.prompt_for_download":   False,
            "download.directory_upgrade":     True,
            "safebrowsing.enabled":           True,
        })

        service = Service(EdgeChromiumDriverManager().install())
        self.driver = webdriver.Edge(service=service, options=options)
        self.driver.implicitly_wait(10)

    # ── 컨텍스트 매니저 ─────────────────────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        try:
            self.driver.quit()
        except Exception:
            pass

    # ── 기본 조작 ──────────────────────────────────────────────────────────

    def goto(self, url: str, wait: float = 1.0):
        self.driver.get(url)
        time.sleep(wait)

    def click(self, css_selector: str, wait: float = 0.5):
        from selenium.webdriver.common.by import By
        el = self.driver.find_element(By.CSS_SELECTOR, css_selector)
        el.click()
        time.sleep(wait)

    def click_xpath(self, xpath: str, wait: float = 0.5):
        from selenium.webdriver.common.by import By
        el = self.driver.find_element(By.XPATH, xpath)
        el.click()
        time.sleep(wait)

    def type(self, css_selector: str, text: str, clear: bool = True):
        from selenium.webdriver.common.by import By
        el = self.driver.find_element(By.CSS_SELECTOR, css_selector)
        if clear:
            el.clear()
        el.send_keys(text)

    def wait_for(self, css_selector: str, timeout: int = 15):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )

    def text(self, css_selector: str) -> str:
        from selenium.webdriver.common.by import By
        try:
            return self.driver.find_element(By.CSS_SELECTOR, css_selector).text
        except Exception:
            return ""

    def html(self) -> str:
        return self.driver.page_source

    def screenshot(self, path: str = "output/screenshot.png"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.driver.save_screenshot(path)
        return path

    def current_url(self) -> str:
        return self.driver.current_url

    # ── 다운로드 대기 ───────────────────────────────────────────────────────

    def wait_for_download(self, extension: str = ".xlsx", timeout: int = 60) -> Optional[str]:
        """다운로드 폴더에서 지정 확장자 파일이 생길 때까지 대기. 파일 경로 반환."""
        import glob
        start = time.time()
        while time.time() - start < timeout:
            files = glob.glob(os.path.join(self._download_dir, f"*{extension}"))
            # .crdownload(크롬 미완성 파일) 제외
            completed = [f for f in files if not f.endswith(".crdownload")]
            if completed:
                newest = max(completed, key=os.path.getmtime)
                return newest
            time.sleep(1)
        return None

    # ── JavaScript 실행 ────────────────────────────────────────────────────

    def js(self, script: str):
        return self.driver.execute_script(script)

    # ── 쿠키/세션 ──────────────────────────────────────────────────────────

    def save_cookies(self, path: str = "config/browser_cookies.json"):
        import json
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.driver.get_cookies(), f, ensure_ascii=False, indent=2)
        print(f"  쿠키 저장: {path}")

    def load_cookies(self, path: str = "config/browser_cookies.json"):
        import json
        if not Path(path).exists():
            return
        with open(path, encoding="utf-8") as f:
            cookies = json.load(f)
        for cookie in cookies:
            try:
                self.driver.add_cookie(cookie)
            except Exception:
                pass
        self.driver.refresh()
        print(f"  쿠키 로드: {path}")
