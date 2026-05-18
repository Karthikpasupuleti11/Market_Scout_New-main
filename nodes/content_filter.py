"""
Market Intelligence Scout — Content Filter Node

Batched LLM classification: multiple articles per completion (fewer API calls).
Falls back to per-article calls if JSON parse fails.
"""

import logging
from typing import Any, Dict, List, Tuple

from graph.state import GraphState
from llm.nvidia_client import invoke_llm
from nodes.llm_article_batches import chunk_list, parse_json_array

logger = logging.getLogger(__name__)


def _classify_one(article: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Return (article, accepted). Single-article path (fallback)."""
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
        logger.debug(
            "CONTENT FILTER — %s: %s",
            "ACCEPT" if accepted else "REJECT",
            title[:60],
        )
        return article, accepted
    except Exception as exc:
        logger.warning(
            "CONTENT FILTER — LLM error for '%s': %s — defaulting to ACCEPT",
            title[:40],
            exc,
        )
        return article, True


def _classify_batch(articles: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], bool]]:
    """One LLM call for len(articles) items; returns aligned (article, accepted)."""
    if len(articles) == 1:
        return [_classify_one(articles[0])]

    from app.config import settings

    blocks = []
    for i, a in enumerate(articles):
        title = (a.get("title") or "N/A")[:200]
        url = (a.get("url") or "")[:500]
        snippet = (a.get("article_text") or "")[:400]
        blocks.append(f"[{i}] URL: {url}\nTitle: {title}\nExcerpt: {snippet}")

    user_prompt = f"""You classify multiple articles for a Market Intelligence system.

For EACH article below (indexed 0..{len(articles) - 1}), output ACCEPT or REJECT.

Rules — ACCEPT if the article contains:
  API/SDK updates, new model/product releases with technical specs, architecture changes,
  developer documentation updates, or performance benchmarks.

Rules — REJECT if:
  stock/financial analysis, HR/restructuring, pure opinion, marketing fluff without
  technical substance, or legal/regulatory news without technical detail.

ARTICLES:
{chr(10).join(blocks)}

Return ONLY a JSON array (no markdown) with one object per index, in order:
[{{"index": 0, "decision": "ACCEPT"}}, {{"index": 1, "decision": "REJECT"}}, ...]
Use exactly indices 0 through {len(articles) - 1}."""

    messages = [
        {
            "role": "system",
            "content": "You output ONLY valid JSON arrays. Each element has keys index (int) and decision (ACCEPT or REJECT).",
        },
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = invoke_llm(
            messages,
            temperature=0.0,
            max_tokens=min(256, 32 * len(articles) + 64),
        )
        arr = parse_json_array(response)
        decisions: Dict[int, bool] = {}
        for item in arr:
            if not isinstance(item, dict):
                continue
            idx = item.get("index")
            if idx is None:
                continue
            try:
                idx = int(idx)
            except (TypeError, ValueError):
                continue
            dec = str(item.get("decision", "")).strip().upper()
            decisions[idx] = "ACCEPT" in dec

        out: List[Tuple[Dict[str, Any], bool]] = []
        for i, art in enumerate(articles):
            out.append((art, decisions.get(i, True)))
        return out
    except Exception as exc:
        logger.warning(
            "CONTENT FILTER — Batch parse failed (%d articles): %s — falling back per-article",
            len(articles),
            exc,
        )
        return [_classify_one(a) for a in articles]


def content_filter_node(state: GraphState) -> Dict[str, Any]:
    articles = state.get("filtered_results", [])
    logger.info("CONTENT FILTER — Evaluating %d articles", len(articles))

    if not articles:
        return {"filtered_results": []}

    from app.config import settings

    batch_size = max(1, settings.LLM_BATCH_CONTENT_FILTER)
    validated: List[Dict[str, Any]] = []

    for batch in chunk_list(articles, batch_size):
        for article, accepted in _classify_batch(batch):
            if accepted:
                validated.append(article)

    logger.info("CONTENT FILTER — %d/%d articles passed", len(validated), len(articles))
    return {"filtered_results": validated}
