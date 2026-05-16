# app/rag/service.py

from app.rag.embedding import embed, chunk_text
from app.rag.pdf_loader import load_pdf
from app.rag.vector_store import VectorStore
from llm.nvidia_client import invoke_llm
from cache.redis_client import get_redis

REDIS_KEY = "rag_index"


async def process_pdf(file):
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
    redis.set(REDIS_KEY, store.serialize(), ex=3600)  # ⏳ 1 hour expiry


def process_report_text(company_name, executive_summary, features, all_sources):
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

    # ── Chunk, embed, and store ──────────────────────────────────────
    raw_chunks = chunk_text(full_text)
    all_chunks = [{"text": c["text"], "page": 1} for c in raw_chunks]

    embeddings = embed([c["text"] for c in all_chunks])

    store = VectorStore()
    store.build(embeddings, all_chunks)

    redis = get_redis()
    redis.set(REDIS_KEY, store.serialize(), ex=3600)  # ⏳ 1 hour expiry


def load_store():
    redis = get_redis()
    data = redis.get(REDIS_KEY)

    if not data:
        return None

    store = VectorStore()
    store.deserialize(data)
    return store


async def ask_question(query: str):
    store = load_store()
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
2. If the user asks a general question (e.g. "what is RAG?", "how are you?", "explain transformers"), answer using your general knowledge — but keep it concise and helpful.
3. If the user asks something that COULD be in the report but isn't, say something like: "The report doesn't cover this specific topic, but here's what I know generally: ..."
4. Be conversational and natural. Don't be robotic.
5. When answering from the report, mention it naturally (e.g. "According to the report..." or "The analysis found that...").
6. Keep answers concise — 2-4 sentences for simple questions, more for detailed analysis questions."""
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
    except Exception as e:
        print("LLM ERROR:", e)

        return {
            "answer": "Unable to generate answer right now. Please try again.",
            "sources": chunks
        }

    return {
        "answer": response,
        "sources": chunks
    }