"""
Playwright scraper.

NOTE: a fresh sync_playwright() context is created per call on purpose.
The scraper agent invokes scrape() from a ThreadPoolExecutor, and the
Playwright sync API is not thread-safe — a shared browser cannot be driven
from multiple threads. Per-call context is thread-safe and leak-free
(the context manager stops the node driver on exit).

A process-global semaphore caps concurrent Chromium instances to prevent
memory explosion (~400MB per browser). Default limit: 3.
"""

import threading
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from .cleaners import clean_soup
from .dates import from_meta, from_text

# ── Concurrency control ────────────────────────────────────────────
# Lazy-init: read limit from settings only once, at first use.
_browser_semaphore = None
_sem_lock = threading.Lock()


def _get_semaphore() -> threading.Semaphore:
    """Return the process-global Playwright semaphore (lazy init)."""
    global _browser_semaphore
    if _browser_semaphore is None:
        with _sem_lock:
            if _browser_semaphore is None:
                try:
                    from app.config import settings
                    limit = settings.PLAYWRIGHT_MAX_CONCURRENT
                except Exception:
                    limit = 3
                _browser_semaphore = threading.Semaphore(limit)
    return _browser_semaphore


def scrape(url: str):
    sem = _get_semaphore()
    sem.acquire()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, timeout=15000)
                html = page.content()
            finally:
                browser.close()

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
    finally:
        sem.release()

