from app.rag.embedding import chunk_text, embed
from app.rag.vector_store import VectorStore


def test_rag_pipeline_integration():

    # STEP 1 — Sample document
    text = """
    OpenAI released a new GPT model with improved reasoning.
    The API now supports structured outputs and tool calling.
    """

    # STEP 2 — Chunking
    chunks = chunk_text(
        text,
        chunk_size=100,
        overlap=20
    )

    assert len(chunks) > 0

    # STEP 3 — Embeddings
    embeddings = embed(
        [c["text"] for c in chunks]
    )

    assert len(embeddings) == len(chunks)

    # STEP 4 — Build vector store
    store = VectorStore()

    store.build(
        embeddings,
        chunks
    )

    assert store.index is not None

    # STEP 5 — Query embedding
    query = "What new API features were released?"

    query_embedding = embed([query])

    # STEP 6 — Search
    results = store.search(
        query_embedding,
        k=2
    )

    assert len(results) > 0

    # STEP 7 — Validate semantic retrieval
    retrieved_text = results[0]["text"].lower()

    assert (
        "api" in retrieved_text
        or "tool calling" in retrieved_text
        or "structured outputs" in retrieved_text
    )