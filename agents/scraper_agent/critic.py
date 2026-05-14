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


def is_technical(text: str) -> bool:
    """Return True if the text looks technical enough to keep.

    Cheap pre-filter only — the content_filter node is the authoritative gate.
    """
    if not text:
        return False
    low = text[:3000].lower()
    hits = sum(1 for kw in TECH_KEYWORDS if kw in low)
    return hits >= MIN_KEYWORD_HITS
