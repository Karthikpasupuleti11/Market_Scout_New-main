"""
Scraper critic — cheap keyword heuristic.

Previously made an LLM call per scraped article (~15-30s on NVIDIA NIM).
That judgment is redundant: the content_filter node runs a precise LLM
classifier downstream (and now in parallel). This heuristic only drops
obvious non-technical junk for free, with zero API latency.
"""

TECH_KEYWORDS = {
    "api", "sdk", "release", "model", "feature", "update", "launch",
    "version", "infrastructure", "platform", "framework", "benchmark",
    "performance", "integration", "deploy", "open source", "open-source",
    "github", "algorithm", "architecture", "latency", "throughput",
    "inference", "training", "dataset", "endpoint", "library", "runtime",
    "gpu", "compute", "changelog", "developer", "documentation",
}

MIN_KEYWORD_HITS = 3


async def is_technical(text: str) -> bool:

    prompt = f"""
Determine if this content contains REAL technical updates
(APIs, SDKs, infra, models, releases).

Respond ONLY in valid JSON:
{{ "technical": true }}

Text:
{text[:1200]}
"""

    raw_response = invoke_llm(
        [{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=50,
    )

    # 🔥 Handle string safely
    if isinstance(raw_response, str):
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError:
            return False

    elif isinstance(raw_response, dict):
        parsed = raw_response

    else:
        return False
    low = text[:3000].lower()
    hits = sum(1 for kw in TECH_KEYWORDS if kw in low)
    return hits >= MIN_KEYWORD_HITS
