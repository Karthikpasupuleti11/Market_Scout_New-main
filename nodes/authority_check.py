"""
Market Intelligence Scout — Authority Check Node

Batched LLM source-credibility classification (fewer API calls).
Falls back to per-article calls if JSON parse fails.
"""

import logging
from typing import Any, Dict, List

from graph.state import GraphState
from llm.nvidia_client import invoke_llm
from nodes.llm_article_batches import chunk_list, parse_json_array

logger = logging.getLogger(__name__)


def _classify_one(article: Dict[str, Any], company_name: str) -> Dict[str, Any]:
    title = article.get("title", "N/A")
    url = article.get("url", "")

    prompt = f"""You are an enterprise source-credibility classifier.

Determine if this article is an OFFICIAL or PRIMARY technical source for {company_name}.

PRIMARY sources include:
  - Official company blogs, docs, or changelogs
  - GitHub repositories owned by {company_name}
  - First-party developer documentation
  - Official press releases with technical detail

SECONDARY sources include:
  - News aggregation sites reporting about {company_name}
  - Third-party commentary or analysis
  - Community discussions

Title: {title}
URL: {url}

Respond with ONLY one word: PRIMARY or SECONDARY"""

    messages = [
        {
            "role": "system",
            "content": "You are a strict source classifier. Respond with one word.",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        response = invoke_llm(messages, temperature=0.0, max_tokens=10)
        decision = response.strip().upper()

        if "PRIMARY" in decision:
            logger.debug("AUTHORITY — PRIMARY: %s", url[:60])
            return article

        article_copy = dict(article)
        article_copy["authority_score"] = article_copy.get("authority_score", 0.5) * 0.7
        logger.debug("AUTHORITY — SECONDARY (reduced score): %s", url[:60])
        return article_copy

    except Exception as exc:
        logger.warning(
            "AUTHORITY — LLM error for '%s': %s — defaulting to include",
            url[:40],
            exc,
        )
        return article


def _classify_batch(articles: List[Dict[str, Any]], company_name: str) -> List[Dict[str, Any]]:
    if len(articles) == 1:
        return [_classify_one(articles[0], company_name)]

    blocks = []
    for i, a in enumerate(articles):
        title = (a.get("title") or "N/A")[:200]
        url = (a.get("url") or "")[:500]
        blocks.append(f"[{i}] URL: {url}\nTitle: {title}")

    user_prompt = f"""Classify each article as PRIMARY or SECONDARY for technical credibility regarding {company_name}.

PRIMARY: official blogs/docs/changelogs, first-party GitHub repos, developer documentation, official technical releases.
SECONDARY: news sites, third-party analysis, community posts.

ARTICLES:
{chr(10).join(blocks)}

Return ONLY a JSON array (no markdown), one object per index 0..{len(articles) - 1}:
[{{"index": 0, "tier": "PRIMARY"}}, {{"index": 1, "tier": "SECONDARY"}}, ...]
tier must be exactly PRIMARY or SECONDARY."""

    messages = [
        {
            "role": "system",
            "content": "You output ONLY valid JSON arrays. Each object has index (int) and tier (PRIMARY or SECONDARY).",
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
        is_primary: Dict[int, bool] = {}
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
            tier = str(item.get("tier", "")).strip().upper()
            if "SECONDARY" in tier:
                is_primary[idx] = False
            elif "PRIMARY" in tier:
                is_primary[idx] = True
            else:
                is_primary[idx] = True

        out: List[Dict[str, Any]] = []
        for i, art in enumerate(articles):
            if is_primary.get(i, True):
                out.append(art)
            else:
                copy = dict(art)
                copy["authority_score"] = copy.get("authority_score", 0.5) * 0.7
                out.append(copy)
        return out
    except Exception as exc:
        logger.warning(
            "AUTHORITY — Batch failed (%d articles): %s — per-article fallback",
            len(articles),
            exc,
        )
        return [_classify_one(a, company_name) for a in articles]


def authority_check_node(state: GraphState) -> Dict[str, Any]:
    articles = state.get("filtered_results", [])
    company_name = state.get("company_name", "")
    logger.info(
        "AUTHORITY CHECK — Evaluating %d articles for '%s'",
        len(articles),
        company_name,
    )

    if not articles:
        return {"filtered_results": []}

    from app.config import settings

    batch_size = max(1, settings.LLM_BATCH_AUTHORITY)
    validated: List[Dict[str, Any]] = []

    for batch in chunk_list(articles, batch_size):
        validated.extend(_classify_batch(batch, company_name))

    logger.info("AUTHORITY CHECK — %d articles passed", len(validated))
    return {"filtered_results": validated}
