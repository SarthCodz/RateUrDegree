import numpy as np
from typing import List, Dict, Any
from google import genai

class BulletinRAG:
    def __init__(self, client: genai.Client):
        self.client = client
        self.chunks: List[Dict[str, str]] = []
        self.embeddings: List[np.ndarray] = []

    def chunk_bulletin(self, program_name: str, bulletin_text: str, chunk_size: int = 800) -> None:
        """Split bulletin text into program-specific chunks."""
        paragraphs = [p.strip() for p in bulletin_text.split("\n\n") if p.strip()]
        for idx, paragraph in enumerate(paragraphs):
            self.chunks.append({
                "program": program_name,
                "section": f"Section {idx + 1}",
                "text": paragraph
            })

    def build_vector_store(self) -> None:
        """Generate embeddings using gemini-embedding-001."""
        if not self.chunks:
            return
            
        texts = [c["text"] for c in self.chunks]
        response = self.client.models.embed_content(
            model="gemini-embedding-001",
            contents=texts
        )
        
        for embedding in response.embeddings:
            self.embeddings.append(np.array(embedding.values, dtype=np.float32))

    def retrieve_top_k(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve top-k relevant chunks using cosine similarity."""
        query_resp = self.client.models.embed_content(
            model="gemini-embedding-001",
            contents=query
        )
        query_vec = np.array(query_resp.embeddings[0].values, dtype=np.float32)

        similarities = []
        for vec in self.embeddings:
            sim = np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec) + 1e-10)
            similarities.append(sim)

        top_indices = np.argsort(similarities)[-k:][::-1]
        return [self.chunks[i] for i in top_indices]

    def query_with_citations(self, query: str) -> str:
        """Generate response with explicit program/section citations."""
        retrieved_chunks = self.retrieve_top_k(query, k=3)
        
        context_str = "\n\n".join([
            f"[{c['program']} | {c['section']}]: {c['text']}"
            for c in retrieved_chunks
        ])

        prompt = f"""
        Answer the following student question based strictly on the retrieved context below.
        You MUST cite the source program and section for every claim made in your response.

        RETRIEVED CONTEXT:
        {context_str}

        QUESTION:
        {query}
        """

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text