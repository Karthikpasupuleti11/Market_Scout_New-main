from typing import Dict, Any, List
import traceback
from graph.state import GraphState
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

from .memory import get_article, save_article, load_agent_memory, save_agent_memory
from .planner import decide_strategy
from .critic import is_technical
from .tools import newspaper, bs4, playwright
from observability.metrics import SCRAPER_ATTEMPTS

logger = logging.getLogger(__name__)

TOOLS = {
    "newspaper3k": newspaper.scrape,
    "beautifulsoup": bs4.scrape,
    "playwright": playwright.scrape,
}

MAX_FAILURES_PER_URL = 3
MAX_WORKERS = 10


async def process_single_url(item, company):
    url = item["url"]
    failures = 0

    logger.info("SCRAPER — Processing URL | %s", url)

    # ── Cache check ─────────────────────────────
    cached = get_article(url)
    if cached:
        logger.info("SCRAPER — Cache hit | %s", url)
        return cached

    strategies = await decide_strategy(url)
    result = None

    # ── Try strategies ─────────────────────────
    for strategy in strategies:
        try:
            logger.info("SCRAPER — Trying tool: %s", strategy)
            result = await asyncio.to_thread(TOOLS[strategy], url)

            if result and result.get("text"):
                logger.info("SCRAPER — Tool succeeded: %s", strategy)
                SCRAPER_ATTEMPTS.labels(strategy=strategy, status="success").inc()
                break

            SCRAPER_ATTEMPTS.labels(strategy=strategy, status="failure").inc()
            failures += 1

        except Exception as e:
            SCRAPER_ATTEMPTS.labels(strategy=strategy, status="failure").inc()
            failures += 1
            logger.debug("SCRAPER — Tool exception | %s | %s", strategy, str(e))

        if failures >= MAX_FAILURES_PER_URL:
            logger.warning(
                "SCRAPER — Skipping URL after %d failures | %s",
                failures,
                url,
            )
            return None

    if not result or not result.get("text"):
        return None

    # ── Critic ─────────────────────────────────
    technical = await is_technical(result["text"])

    logger.info("SCRAPER — Critic decision | Technical: %s", technical)

    if not technical:
        return None

    article = {
        "url": url,
        "title": result.get("title"),
        "article_text": result["text"],
        "publish_date": str(result.get("date")) if result.get("date") else None,
        "scraper_used": result.get("tool"),
    }

    save_article(url, article)

    logger.info("SCRAPER — Article saved | Tool: %s", result.get("tool"))

    return article


async def scraper_agent_node(state: GraphState) -> Dict[str, Any]:

    start_time = time.time()

    urls = state.get("search_results", [])
    company = state.get("company_name")

    logger.info(
        "SCRAPER AGENT — Started | Company: %s | URLs received: %d",
        company,
        len(urls),
    )

    memory = load_agent_memory(company)

    # 🚀 TRUE ASYNC PARALLEL SCRAPING
    tasks = [
        process_single_url(item, company)
        for item in urls
    ]

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True
    )

    scraped = []

    for result in results:

        if isinstance(result, Exception):
            # Log the exception type/message and full traceback to diagnose formatting errors
            logger.warning("SCRAPER — Task failed | %s", repr(result))
            logger.debug("SCRAPER — Traceback:\n%s", "".join(traceback.format_exception(type(result), result, result.__traceback__)))
            continue

        if result:
            scraped.append(result)

    save_agent_memory(company, memory)

    logger.info(
        "SCRAPER AGENT — Completed | Articles scraped: %d | Time: %.2fs",
        len(scraped),
        time.time() - start_time,
    )

    return {
        "scraped_articles": scraped
    }