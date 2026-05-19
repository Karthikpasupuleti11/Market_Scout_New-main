"""RAG indexing and Q&A over the active report (demo: single shared index in Redis)."""

import logging

from app.rag.embedding import embed, chunk_text
from app.rag.pdf_loader import load_pdf
from app.rag.vector_store import VectorStore
from llm.nvidia_client import invoke_llm
from cache.redis_client import get_redis

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "rag_index"


def _redis_key(session_id: str) -> str:
    if not session_id:
        raise ValueError("session_id is required for RAG operations")
    return f"{REDIS_KEY_PREFIX}:{session_id}"


async def process_pdf(file, session_id: str):
    pages = load_pdf(file)

    all_chunks = []

    for page in pages:
        chunks = chunk_text(page["text"])

        for c in chunks:
            all_chunks.append({
                "text": c["text"],
                "page": page["page"]
            })

    embeddings = embed([c["text"] for c in all_chunks])

    store = VectorStore()
    store.build(embeddings, all_chunks)

    redis = get_redis()
    redis.set(_redis_key(session_id), store.serialize(), ex=3600)  # ⏳ 1 hour expiry


def process_report_text(company_name, executive_summary, features, all_sources, session_id=None):
    """Convert structured report data into plain-text chunks, embed, and store
    in the vector store so the user can query the report via RAG."""

    # ── Build a rich text document from the report data ──────────────
    sections = []

    # Executive summary
    if executive_summary:
        sections.append(
            f"Executive Summary for {company_name}:\n{executive_summary}"
        )

    # Each feature as a standalone paragraph
    for i, feat in enumerate(features or [], 1):
        title = feat.get("title") or feat.get("feature_title") or f"Signal {i}"
        desc = feat.get("description") or feat.get("feature_summary") or ""
        category = feat.get("category") or "General"
        confidence = feat.get("confidence_score") or feat.get("confidence") or 0
        impact = feat.get("impact_assessment") or ""
        metrics = feat.get("key_metrics") or []
        source_url = feat.get("source_url") or ""

        parts = [f"Signal #{i} — {title} (Category: {category}, Confidence: {confidence:.0%})"]
        if desc:
            parts.append(f"Description: {desc}")
        if impact:
            parts.append(f"Impact: {impact}")
        if metrics:
            parts.append(f"Key Metrics: {', '.join(str(m) for m in metrics)}")
        if source_url:
            parts.append(f"Source: {source_url}")
        sections.append("\n".join(parts))

    # Sources section
    if all_sources:
        sources_text = "\n".join(f"  - {url}" for url in all_sources)
        sections.append(f"All Sources Analyzed:\n{sources_text}")

    full_text = "\n\n".join(sections)

    if not full_text.strip():
        logger.warning("RAG — Empty report text, skipping indexing")
        return

    # ── Chunk, embed, and store ──────────────────────────────────────
    raw_chunks = chunk_text(full_text)
    all_chunks = [{"text": c["text"], "page": 1} for c in raw_chunks]

    embeddings = embed([c["text"] for c in all_chunks])

    store = VectorStore()
    store.build(embeddings, all_chunks)

    # Use company name as fallback key if no session_id provided
    key = _redis_key(session_id) if session_id else f"{REDIS_KEY_PREFIX}:{company_name.lower().replace(' ', '_')}"

    redis = get_redis()
    redis.set(key, store.serialize(), ex=3600)  # ⏳ 1 hour expiry
    logger.info("RAG — Report indexed for '%s' (key=%s, chunks=%d)", company_name, key, len(all_chunks))


def load_store(session_id: str):
    redis = get_redis()
    data = redis.get(_redis_key(session_id))

    if not data:
        return None

    store = VectorStore()
    store.deserialize(data)
    return store


async def process_report(report: dict, session_id: str):

    print("PROCESS REPORT STARTED")

    sections = []

    # ── Executive Summary ─────────────────────────
    sections.append(
        f"""
Company:
{report.get('company_name', '')}

Executive Summary:
{report.get('executive_summary', '')}
"""
    )

    # ── Features ─────────────────────────────────
    for feature in report.get("features", []):

        metrics = feature.get("key_metrics") or []

        # Safe handling
        if not isinstance(metrics, list):
            metrics = [str(metrics)]

        section = f"""
Feature Title:
{feature.get('title', '')}

Description:
{feature.get('description', '')}

Category:
{feature.get('category', '')}

Impact:
{feature.get('impact_assessment', '')}

Metrics:
{', '.join(metrics)}
"""

        sections.append(section)

    # ── Final Text ───────────────────────────────

    full_text = "\n\n".join(sections).strip()

    if not full_text:
        raise Exception("Empty report text")

    # ── Chunking ─────────────────────────────────

    chunks = chunk_text(full_text)

    all_chunks = []

    for c in chunks:

        all_chunks.append({
            "text": c["text"],
            "page": "report"
        })

    print(f"TOTAL CHUNKS: {len(all_chunks)}")

    # ── Embeddings ───────────────────────────────

    embeddings = embed(
        [c["text"] for c in all_chunks]
    )

    # ── Vector Store ─────────────────────────────

    store = VectorStore()

    store.build(
        embeddings,
        all_chunks
    )

    # ── Redis Save ───────────────────────────────

    redis = get_redis()

    redis.set(
        _redis_key(session_id),
        store.serialize(),
        ex=3600
    )

    print("RAG INDEX STORED SUCCESSFULLY")


async def ask_question(query: str, session_id: str):
    store = load_store(session_id)
    if not store:
        return {"answer": "No document uploaded.", "sources": []}

    # Detect broad/summary questions
    broad_keywords = ["about", "summarize", "summary", "overview", "what is",
                      "company", "topic", "describe", "explain"]
    is_broad = any(kw in query.lower() for kw in broad_keywords)

    k = 8 if is_broad else 4  # Fetch more chunks for broad questions

    query_embedding = embed([query])
    chunks = store.search(query_embedding, k=k)
    context = "\n\n".join([c["text"] for c in chunks])

    messages = [
        {
            "role": "system",
            "content": """You are a smart Report Assistant for a competitive intelligence platform called Market Scout.
You have access to excerpts from an intelligence report about a company.

RULES:
1. If the user's question relates to the report content, answer using the provided context. Cite specific signals, metrics, or findings from the report.
2. If the user asks a general question (e.g. "what is RAG?", "how are you?"), answer using your general knowledge — keep it concise.
3. If the user asks something that COULD be in the report but isn't, say: "The report doesn't cover this, but here's what I know..."
4. Be conversational but organized. Sound like a knowledgeable analyst briefing a colleague.
5. When answering from the report, reference it naturally (e.g. "According to the report..." or "The analysis found...").

FORMATTING RULES (CRITICAL — follow these exactly):
- Use numbered lists (1, 2, 3...) when listing multiple signals, features, or findings.
- Use arrows (→) to show cause-effect or key takeaways.
- Use line breaks between sections for readability.
- For key metrics or confidence scores, include them inline like: (Confidence: 95%)
- Do NOT use markdown. No ** for bold, no # for headers, no ``` for code blocks, no * for bullets.
- Keep it clean and structured — like a professional briefing, not a chatbot wall of text.

EXAMPLE FORMAT:
The report identifies 3 key signals for Google:

1. Offline Conversion Import → Enables developers to import offline conversions via the Ads API (Confidence: 95%)
2. Experiment Functionality v24.1 → Provides arm-level stats for more informed decisions
3. Quick Share Cross-Platform → QR-code based transfer between Android and iOS

Key takeaway → All signals show high confidence (95%), indicating strong verification across sources."""
        },
        {
            "role": "user",
            "content": f"""Here are excerpts from the intelligence report for context:
---
{context}
---

User question: {query}"""
        }
    ]

    try:
        response = await invoke_llm(messages)
    except Exception as exc:
        logger.warning("RAG — LLM call failed: %s", exc)
        return {
            "answer": "Unable to generate answer right now. Please try again.",
            "sources": chunks,
        }

    return {
        "answer": response,
        "sources": chunks
    }