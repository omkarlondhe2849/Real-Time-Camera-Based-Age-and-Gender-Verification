"""
conftest.py  –  Pytest fixtures shared across all test modules.

Starts the Flask app in a background thread and provides a
configured Selenium WebDriver for each test session.
"""

import threading
import time
import os
import sys
import pytest

# ── ensure project root is importable ────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "http://127.0.0.1:5000"


# ── Selenium WebDriver fixture (function-scoped – fresh browser per test) ─────
@pytest.fixture
def driver():
    """Return a headless Chrome WebDriver with fake camera support."""
    opts = Options()
    opts.add_argument("--headless=new")          # headless Chrome
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    # Allow fake webcam/microphone so getUserMedia works in headless mode
    opts.add_argument("--use-fake-ui-for-media-stream")
    opts.add_argument("--use-fake-device-for-media-stream")
    opts.add_argument("--allow-file-access-from-files")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])

    drv = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts,
    )
    drv.set_page_load_timeout(30)
    drv.implicitly_wait(5)

    yield drv
    drv.quit()
