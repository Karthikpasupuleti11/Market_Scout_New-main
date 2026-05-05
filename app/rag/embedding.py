# app/rag/embedding.py

from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def chunk_text(text, chunk_size=500, overlap=50):
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size]
        chunks.append({
            "text": chunk,
            "chunk_id": i
        })
    return chunks


def embed(texts):
    return model.encode(texts)