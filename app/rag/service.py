# app/rag/service.py

from app.rag.embedding import embed, chunk_text
from app.rag.pdf_loader import load_pdf
from app.rag.vector_store import VectorStore
from llm.nvidia_client import invoke_llm
from cache.redis_client import get_redis

REDIS_KEY = "rag_index"


def process_pdf(file):
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


def ask_question(query: str):
    store = load_store()

    if not store:
        return {
            "answer": "No document uploaded.",
            "sources": []
        }

    query_embedding = embed([query])
    chunks = store.search(query_embedding, k=4)

    context = "\n\n".join([c["text"] for c in chunks])

    messages = [
        {
            "role": "system",
            "content": "Answer ONLY from the context. If not found, say 'Not in report'."
        },
        {
            "role": "user",
            "content": f"""
Context:
{context}

Question:
{query}
"""
        }
    ]

    try:
        response = invoke_llm(messages)
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