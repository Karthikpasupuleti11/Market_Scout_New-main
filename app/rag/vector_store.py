"""In-memory FAISS vector store with Redis-backed serialization (demo / presentation)."""

import base64
import pickle

import faiss
import numpy as np


class VectorStore:
    def __init__(self):
        self.index = None
        self.chunks = []

    def build(self, embeddings, chunks):
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(np.array(embeddings))
        self.chunks = chunks

    def search(self, query_embedding, k=4):
        distances, indices = self.index.search(query_embedding, k)
        return [self.chunks[i] for i in indices[0]]

    def serialize(self):
        data = pickle.dumps({
            "index": faiss.serialize_index(self.index),
            "chunks": self.chunks,
        })
        return base64.b64encode(data).decode("utf-8")

    def deserialize(self, data):
        raw = base64.b64decode(data.encode("utf-8"))
        obj = pickle.loads(raw)
        self.index = faiss.deserialize_index(obj["index"])
        self.chunks = obj["chunks"]
