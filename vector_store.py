# vector_store.py
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from typing import List

class VectorStore:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.encoder = SentenceTransformer(model_name)
        self.index = None
        self.chunks = []        # original text chunks
        self.embeddings = None  # stored for potential reuse

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split long text into overlapping chunks of approximately chunk_size characters.
        """
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i+chunk_size])
            chunks.append(chunk)
        return chunks

    def build_index(self, chunks: List[str]):
        """Create FAISS index from chunks."""
        self.chunks = chunks
        if not chunks:
            raise ValueError("No chunks to index.")
        embeddings = self.encoder.encode(chunks, convert_to_numpy=True)
        self.embeddings = embeddings
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings)

    def search(self, query: str, top_k: int = 3) -> List[str]:
        """Return the top_k most similar chunks for a query."""
        if self.index is None:
            raise RuntimeError("Index not built. Call build_index() first.")
        query_emb = self.encoder.encode([query], convert_to_numpy=True)
        distances, indices = self.index.search(query_emb, top_k)
        # Return chunks sorted by similarity
        return [self.chunks[i] for i in indices[0]]