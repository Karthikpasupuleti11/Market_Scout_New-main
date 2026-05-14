"""
Playwright scraper.

NOTE: a fresh sync_playwright() context is created per call on purpose.
The scraper agent invokes scrape() from a ThreadPoolExecutor, and the
Playwright sync API is not thread-safe — a shared browser cannot be driven
from multiple threads. Per-call context is thread-safe and leak-free
(the context manager stops the node driver on exit).
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from .cleaners import clean_soup
from .dates import from_meta, from_text


def scrape(url: str):
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
