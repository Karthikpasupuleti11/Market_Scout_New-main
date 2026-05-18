"""
Market Intelligence Scout — Feature Extraction Agent

Batched LLM extraction: multiple articles per completion when possible.
Per-URL Redis cache unchanged. Falls back to one article per call on batch failure.
"""

import json
import re
import logging
from typing import Any, Dict, List

from graph.state import GraphState
from llm.nvidia_client import invoke_llm
from cache.redis_client import make_cache_key, get_cache, set_cache
from nodes.llm_article_batches import chunk_list, parse_json_object

logger = logging.getLogger(__name__)

_BATCH_TEXT_CHARS = 4500


def _clean_json_response(raw: str) -> str:
    cleaned = re.sub(r"```json\s?|\s?```", "", raw).strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]") + 1
    if start != -1 and end > start:
        return cleaned[start:end]
    return cleaned


def feature_extraction_node(state: GraphState) -> Dict[str, Any]:
    """
    Feature Extraction Agent — extracts structured technical features.

    Input:  state["filtered_results"] (from Content Filter)
    Output: state["extracted_features"]
    """
    filtered = state.get("filtered_results", [])
    company_name = state.get("company_name", "")
    logger.info(
        "FEATURE EXTRACTION — Processing %d articles for '%s'",
        len(filtered),
        company_name,
    )

    if not filtered:
        logger.warning("FEATURE EXTRACTION — No articles to process")
        return {"extracted_features": []}

    from app.config import settings

    batch_size = max(1, settings.LLM_BATCH_FEATURE_EXTRACTION)
    all_features: List[Dict[str, Any]] = []

    pending: List[Dict[str, Any]] = []
    for art in filtered:
        url = art.get("url", "")
        cache_key = make_cache_key("features", url)
        hit = get_cache(cache_key)
        if hit is not None:
            all_features.extend(hit if isinstance(hit, list) else [])
        else:
            pending.append(art)

    for batch in chunk_list(pending, batch_size):
        if len(batch) == 1:
            all_features.extend(_extract_one(batch[0], company_name) or [])
            continue
        merged = _extract_batch(batch, company_name)
        if merged is None:
            for art in batch:
                all_features.extend(_extract_one(art, company_name) or [])
        else:
            all_features.extend(merged)

    logger.info(
        "FEATURE EXTRACTION — Total features extracted: %d",
        len(all_features),
    )
    return {"extracted_features": all_features}


def _extract_batch(
    articles: List[Dict[str, Any]],
    company_name: str,
) -> List[Dict[str, Any]] | None:
    """One LLM call for multiple articles, or None to trigger per-article fallback."""
    blocks = []
    for i, a in enumerate(articles):
        url = (a.get("url") or "")[:800]
        text = (a.get("article_text") or "")[:_BATCH_TEXT_CHARS]
        blocks.append(f"### Article index {i}\nURL: {url}\nTEXT:\n{text}\n")

    system_message = {
        "role": "system",
        "content": (
            "You extract technical product features from multiple articles in one response. "
            "Use ONLY text under each article's TEXT section. "
            "If an article has no explicit technical changes, use an empty features array for that index. "
            "NEVER invent features. Output ONLY valid JSON matching the schema — no markdown."
        ),
    }

    user_prompt = f"""Company: {company_name}

For EACH article (indices 0 through {len(articles) - 1}), extract features as JSON objects.
Each feature must have:
  "feature_summary", "feature_title", "category" (model_release|api_update|performance|capability|sdk_update|infrastructure|docs),
  "metrics" (array of strings), "confidence" (number 0-1), "evidence" (short quote from that article's TEXT)

ARTICLES:
{chr(10).join(blocks)}

Return ONLY this JSON object (no markdown):
{{
  "results": [
    {{"index": 0, "features": [ ]}},
    {{"index": 1, "features": [ ]}}
  ]
}}
Include exactly one results entry per index from 0 to {len(articles) - 1}, in order."""

    try:
        from app.config import settings

        response = invoke_llm(
            [system_message, {"role": "user", "content": user_prompt}],
            temperature=0.0,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
        root = parse_json_object(response)
        rows = root.get("results")
        if not isinstance(rows, list):
            return None

        by_index: Dict[int, List[Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                idx = int(row.get("index", -1))
            except (TypeError, ValueError):
                continue
            feats = row.get("features")
            if isinstance(feats, list):
                by_index[idx] = feats

        flat: List[Dict[str, Any]] = []
        for i, article in enumerate(articles):
            url = article.get("url", "")
            feats_raw = by_index.get(i)
            if not isinstance(feats_raw, list):
                return None
            article_features: List[Dict[str, Any]] = []
            for f in feats_raw:
                if not isinstance(f, dict):
                    continue
                f = dict(f)
                f["source_authority"] = article.get("authority_score", 0.5)
                f["url"] = url
                f["publish_date"] = article.get("publish_date")
                article_features.append(f)
                flat.append(f)
            set_cache(make_cache_key("features", url), article_features)

        logger.debug(
            "FEATURE EXTRACTION — Batch OK: %d articles, %d features",
            len(articles),
            len(flat),
        )
        return flat

    except Exception as exc:
        logger.warning(
            "FEATURE EXTRACTION — Batch error (%d articles): %s",
            len(articles),
            exc,
        )
        return None


def _extract_one(article: Dict[str, Any], company_name: str) -> List[Dict[str, Any]]:
    url = article.get("url", "")

    cache_key = make_cache_key("features", url)
    cached = get_cache(cache_key)
    if cached:
        logger.debug("FEATURE EXTRACTION — Cache hit for: %s", url[:60])
        return cached

    article_text = article.get("article_text", "")[:8000]

    system_message = {
        "role": "system",
        "content": (
            "You are a precise extraction engine for technical product updates. "
            "Use ONLY the text provided in DATA. "
            "If a feature, model, parameter, or metric is not EXPLICITLY mentioned in DATA, "
            "do NOT infer, assume, or invent it. "
            "If there are no explicit technical changes in DATA, return an empty JSON list []. "
            "NEVER fabricate feature names, version numbers, or performance metrics."
        ),
    }

    user_prompt = f"""Analyse the following technical update for {company_name}.

TASK: Extract ONLY specific, verifiable technical changes. For each feature, provide:
  - A concise title (max 10 words)
  - A detailed summary (2-3 sentences) explaining WHAT the feature does, HOW it works, and WHY it matters
  - Supporting evidence as a direct quote from the text

DATA:
{article_text}

REQUIRED JSON FORMAT (list of objects):
[
  {{
    "feature_summary": "2-3 sentence detailed explanation of what this feature does, how it works technically, and its practical impact. Use specific details from the article.",
    "feature_title": "Short title (max 10 words)",
    "category": "model_release" | "api_update" | "performance" | "capability" | "sdk_update" | "infrastructure" | "docs",
    "metrics": ["list of numerical data points explicitly stated in DATA"],
    "confidence": 0.0,
    "evidence": "Direct quote from DATA (max 200 chars) that proves this feature exists"
  }}
]

CONSTRAINTS:
  1. Do NOT use outside knowledge — only DATA.
  2. Do NOT invent model names, versions, or benchmarks.
  3. Each feature MUST have a detailed feature_summary (not just the title repeated).
  4. Each feature MUST have supporting evidence (a direct quote).
  5. If no qualifying technical changes exist, return [].

Return ONLY the JSON list. No preamble, no explanation."""

    try:
        response = invoke_llm(
            [system_message, {"role": "user", "content": user_prompt}],
            temperature=0.0,
            max_tokens=settings_max_tokens(),
        )

        cleaned = _clean_json_response(response)
        features = json.loads(cleaned)

        if not isinstance(features, list):
            features = []

        article_features = []
        for f in features:
            f["source_authority"] = article.get("authority_score", 0.5)
            f["url"] = url
            f["publish_date"] = article.get("publish_date")
            article_features.append(f)

        set_cache(cache_key, article_features)

        logger.debug(
            "FEATURE EXTRACTION — Extracted %d features from: %s",
            len(article_features),
            url[:60],
        )
        return article_features

    except json.JSONDecodeError as exc:
        logger.warning(
            "FEATURE EXTRACTION — JSON parse error for %s: %s",
            url[:60],
            exc,
        )
        return []
    except Exception as exc:
        logger.warning("FEATURE EXTRACTION — Error for %s: %s", url[:60], exc)
        return []


def settings_max_tokens() -> int:
    from app.config import settings

    return settings.LLM_MAX_TOKENS
