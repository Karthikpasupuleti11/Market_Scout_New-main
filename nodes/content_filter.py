"""
Market Intelligence Scout — Content Filter Node

Parallelized LLM classification across articles.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple

from graph.state import GraphState
from llm.nvidia_client import invoke_llm

logger = logging.getLogger(__name__)

MAX_PARALLEL = 10


def _classify_one(article: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Return (article, accepted)."""
    title = article.get("title", "N/A")
    text_snippet = article.get("article_text", "")[:600]
    url = article.get("url", "")

    prompt = f"""You are an enterprise content classifier for a Market Intelligence system.

Classify this article's primary intent:

ACCEPT if it contains:
  - API changelogs or SDK updates
  - New model/product releases with technical specs
  - Architecture or infrastructure changes
  - Developer documentation updates
  - Performance benchmark results

REJECT if it is:
  - Stock/financial analysis
  - Corporate restructuring / HR news
  - Opinion articles or commentary
  - Marketing fluff without technical substance
  - Legal or regulatory news

Title: {title}
URL: {url}
Content excerpt:
{text_snippet}

Respond with ONLY one word: ACCEPT or REJECT"""

    messages = [
        {
            "role": "system",
            "content": "You are a strict binary classifier. Respond with exactly one word.",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        response = invoke_llm(messages, temperature=0.0, max_tokens=10)
        decision = response.strip().upper()
        accepted = "ACCEPT" in decision
        logger.debug("CONTENT FILTER — %s: %s", "ACCEPT" if accepted else "REJECT", title[:60])
        return article, accepted
    except Exception as exc:
        logger.warning(
            "CONTENT FILTER — LLM error for '%s': %s — defaulting to ACCEPT",
            title[:40], exc,
        )
        return article, True


def content_filter_node(state: GraphState) -> Dict[str, Any]:
    articles = state.get("filtered_results", [])
    logger.info("CONTENT FILTER — Evaluating %d articles", len(articles))

    if not articles:
        return {"filtered_results": []}

    validated: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL, len(articles))) as pool:
        futures = [pool.submit(_classify_one, art) for art in articles]
        for fut in as_completed(futures):
            article, accepted = fut.result()
            if accepted:
                validated.append(article)

    logger.info("CONTENT FILTER — %d/%d articles passed", len(validated), len(articles))
    return {"filtered_results": validated}
