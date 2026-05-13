"""
Playwright scraper with shared persistent browser.

Launches Chromium once per process, reuses for all URLs.
Each scrape opens a fresh page (isolated cookies/storage).
"""

import atexit
import logging
import threading

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .cleaners import clean_soup
from .dates import from_meta, from_text

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_pw = None
_browser = None


def _get_browser():
    """Lazy-launch Chromium once per process. Thread-safe."""
    global _pw, _browser
    if _browser is not None:
        return _browser
    with _lock:
        if _browser is None:
            _pw = sync_playwright().start()
            _browser = _pw.chromium.launch(headless=True)
            logger.info("PLAYWRIGHT — Chromium launched (shared instance)")
    return _browser


def _shutdown():
    global _pw, _browser
    try:
        if _browser is not None:
            _browser.close()
        if _pw is not None:
            _pw.stop()
    except Exception:
        pass
    _browser = None
    _pw = None


atexit.register(_shutdown)


def scrape(url: str):
    browser = _get_browser()
    context = browser.new_context()
    page = context.new_page()
    try:
        page.goto(url, timeout=15000)
        html = page.content()
    finally:
        page.close()
        context.close()

    soup = clean_soup(BeautifulSoup(html, "html.parser"))
    text = soup.get_text("\n", strip=True)

    if len(text) < 100:
        return None

    return {
        "text": text,
        "title": soup.title.string if soup.title else "",
        "date": from_meta(soup) or from_text(text),
        "tool": "playwright",
    }
