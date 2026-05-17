from typing import Dict, Any, List
import traceback
from graph.state import GraphState
import time
import logging
import asyncio

from .memory import (
    get_article,
    save_article,
    load_agent_memory,
    save_agent_memory,
)

from .planner import decide_strategy
from .critic import batch_is_technical

from .tools import newspaper, bs4, playwright

from observability.metrics import SCRAPER_ATTEMPTS

logger = logging.getLogger(__name__)

TOOLS = {
    "newspaper3k": newspaper.scrape,
    "beautifulsoup": bs4.scrape,
    "playwright": playwright.scrape,
}

MAX_FAILURES_PER_URL = 3


async def process_single_url(item, company):

    url = item["url"]

    failures = 0

    logger.info(
        "SCRAPER — Processing URL | %s",
        url
    )

    # ── Cache ──────────────────────────────
    cached = get_article(url)

    if cached:

        logger.info(
            "SCRAPER — Cache hit | %s",
            url
        )

        return cached

    # ── Strategy ───────────────────────────
    strategies = await decide_strategy(url)

    result = None

    # ── Try strategies ────────────────────
    for strategy in strategies:

        try:

            logger.info(
                "SCRAPER — Trying tool: %s",
                strategy
            )

            result = TOOLS[strategy](url)

            if result and result.get("text"):

                logger.info(
                    "SCRAPER — Tool succeeded: %s",
                    strategy
                )

                SCRAPER_ATTEMPTS.labels(
                    strategy=strategy,
                    status="success"
                ).inc()

                break

            SCRAPER_ATTEMPTS.labels(
                strategy=strategy,
                status="failure"
            ).inc()

            failures += 1

        except Exception as e:

            failures += 1

            SCRAPER_ATTEMPTS.labels(
                strategy=strategy,
                status="failure"
            ).inc()

            logger.debug(
                "SCRAPER — Tool exception | %s | %s",
                strategy,
                str(e)
            )

        if failures >= MAX_FAILURES_PER_URL:

            logger.warning(
                "SCRAPER — Skipping URL after %d failures | %s",
                failures,
                url,
            )

            return None

    if not result or not result.get("text"):
        return None

    return {
        "url": url,
        "title": result.get("title"),
        "text": result["text"],
        "publish_date": (
            str(result.get("date"))
            if result.get("date")
            else None
        ),
        "scraper_used": result.get("tool"),
    }


async def scraper_agent_node(
    state: GraphState
) -> Dict[str, Any]:

    start_time = time.time()

    urls = state.get("search_results", [])

    company = state.get("company_name")

    logger.info(
        "SCRAPER AGENT — Started | Company: %s | URLs received: %d",
        company,
        len(urls),
    )

    memory = load_agent_memory(company)

    # ── Parallel Scraping ───────────────────
    scrape_tasks = [
        process_single_url(item, company)
        for item in urls
    ]

    scrape_results = await asyncio.gather(
        *scrape_tasks,
        return_exceptions=True
    )

    scraped_articles = []

    for result in scrape_results:

        if isinstance(result, Exception):

            logger.warning(
                "SCRAPER — Task failed | %s",
                repr(result)
            )

            logger.debug(
                "SCRAPER — Traceback:\n%s",
                "".join(
                    traceback.format_exception(
                        type(result),
                        result,
                        result.__traceback__,
                    )
                )
            )

            continue

        if result:
            scraped_articles.append(result)

    logger.info(
        "SCRAPER — Raw scraped articles: %d",
        len(scraped_articles)
    )

    if not scraped_articles:

        return {
            "scraped_articles": []
        }

    # ── Batch Technical Critic ─────────────
    technical_results = await batch_is_technical(
        scraped_articles
    )

    filtered_articles = []

    for article, technical in zip(
        scraped_articles,
        technical_results
    ):

        logger.info(
            "SCRAPER — Critic decision | %s | Technical=%s",
            article["url"],
            technical,
        )

        if not technical:
            continue

        # ── Validate article has required text field ──
        article_text = article.get("text") or article.get("article_text")
        
        if not article_text:
            logger.warning(
                "SCRAPER — Skipping article missing text field | %s | Keys: %s",
                article.get("url"),
                list(article.keys())
            )
            continue

        article_data = {
            "url": article["url"],
            "title": article.get("title", ""),
            "article_text": article_text,
            "publish_date": article.get("publish_date"),
            "scraper_used": article.get("scraper_used"),
        }

        save_article(
            article["url"],
            article_data
        )

        filtered_articles.append(article_data)

    save_agent_memory(company, memory)

    logger.info(
        "SCRAPER AGENT — Completed | Articles scraped: %d | Time: %.2fs",
        len(filtered_articles),
        time.time() - start_time,
    )

    return {
        "scraped_articles": filtered_articles
    }