import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from llm.nvidia_client import invoke_llm

logger = logging.getLogger(__name__)


async def plan_queries(
    company: str,
    feedback: Optional[str] = None,
    memory: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Planning brain of the Search Agent.

    Responsibilities:
    - Generate NEW search queries (Tavily-compatible plain language)
    - Respect memory (avoid repeats)
    - Return structured output
    - Fail safely if LLM misbehaves
    """

    attempted = memory.get("attempted_queries", []) if memory else []

    # Inject current date so the LLM doesn't hallucinate old year ranges
    current_month_year = datetime.now().strftime("%B %Y")   # e.g. "April 2026"

    prompt = f"""
You are an autonomous technical search planning agent.

Company:
{company}

Previously attempted queries (DO NOT repeat):
{attempted}

Current date: {current_month_year}

Goal:
Generate 4 NEW plain-language search queries that will find RECENT technical updates
(APIs, SDKs, models, platform changes, infrastructure) released in the LAST 7 DAYS for the company above.

CRITICAL RULES — READ CAREFULLY:
- Write plain natural-language queries, exactly as a person would type them in a search box
- Do NOT use Google search operators: no site:, no inurl:, no intitle:, no filetype:, no date:, no intext:
- Do NOT include date range syntax like "2024-04-09..2024-04-16"
- DO naturally mention "{current_month_year}" or "past week" or "this week" OR "latest 2026" to anchor results to now
- Each query must be distinct and cover a different angle (API, model, SDK, platform, etc.)
- Do NOT repeat previously attempted queries

GOOD query examples (follow this style):
- "{company} new API update {current_month_year}"
- "{company} model release past week"
- "{company} SDK changelog {current_month_year}"
- "{company} platform announcement this week"

Rules:
- Return exactly 4 queries
- Return ONLY valid JSON with no markdown fences and no extra text

Output format:
{{ "queries": ["...", "...", "...", "..."] }}
"""

    if feedback:
        prompt += f"\n\nFeedback from previous iteration (previous queries returned no results):\n{feedback}\nTry completely different query angles.\n"

    # 1️⃣ LLM call (always returns STRING)
    raw_response = await invoke_llm(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=400,
    )

    logger.debug("SEARCH PLANNER — Raw LLM output:\n%s", raw_response)

    # 2️⃣ Strip markdown fences if LLM wrapped in ```json ... ```
    cleaned_response = raw_response.strip()
    if cleaned_response.startswith("```"):
        import re
        cleaned_response = re.sub(r"```[a-z]*\s?|\s?```", "", cleaned_response).strip()

    # 3️⃣ Parse JSON
    try:
        parsed = json.loads(cleaned_response)
    except json.JSONDecodeError as exc:
        logger.error("SEARCH PLANNER — Invalid JSON:\n%s", raw_response)
        raise RuntimeError("Search planner returned invalid JSON") from exc

    # 4️⃣ Validate schema
    queries = parsed.get("queries")

    if not isinstance(queries, list):
        raise RuntimeError("Search planner output missing 'queries' list")

    # Allow 3-5 queries (strict ==4 was too fragile)
    if len(queries) < 1:
        raise RuntimeError(f"Search planner returned empty query list")

    # 5️⃣ Normalize + dedupe against memory
    clean_queries = []
    for q in queries:
        if isinstance(q, str):
            q = q.strip()
            if q and q not in attempted:
                clean_queries.append(q)

    if not clean_queries:
        raise RuntimeError("Search planner produced no usable queries (all were repeats)")

    logger.info(
        "SEARCH PLANNER — Generated %d queries for %s",
        len(clean_queries),
        company,
    )

    return clean_queries