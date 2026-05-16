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
        "content": """You are a helpful document assistant. You are given excerpts from a report.
Answer the user's question using the provided context as your primary source.
- If the answer is directly in the context, answer clearly and concisely.
- If the question is broad (like 'summarize' or 'what is this about'), synthesize from the context chunks available.
- If the context genuinely has no relevant information, say 'The uploaded report does not contain information about this.'
Never say 'Not in report' for general questions that can be reasonably answered from context."""
    },
    {
        "role": "user",
        "content": f"""Context from the document:
{context}

User question: {query}

Please answer based on the above context."""
    }
]

    try:
        response = await invoke_llm(messages)
    except Exception as e:
        print("LLM ERROR:", e)

        return {
            "answer": "⚠️ Unable to generate answer right now. Please try again.",
            "sources": chunks
        }

    return {
        "answer": response,
        "sources": chunks
    }