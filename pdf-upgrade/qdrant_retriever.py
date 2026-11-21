"""Phase 3: actual vector embeddings and Qdrant similarity search."""
from functools import lru_cache
import os
from qdrant_client import QdrantClient, models
from config import QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION, EMBEDDING_MODEL

@lru_cache(maxsize=1)
def embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)

def get_client():
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None, timeout=15)

def query_notes(query: str) -> str:
    client = get_client()
    if not client.collection_exists(QDRANT_COLLECTION):
        return 'Qdrant collection does not exist. Run: python ingest_notes.py'
    vector = embedding_model().encode(query).tolist()
    hits = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=vector,
        with_payload=True,
        limit=3,
        score_threshold=float(os.getenv("RAG_SCORE_THRESHOLD", "0.30")),
    ).points
    if not hits:
        return 'No relevant information found in the indexed study notes or PDFs.'
    results = []
    for hit in hits:
        payload = hit.payload or {}
        topic = payload.get('topic', 'Unknown topic')
        source = payload.get('source', 'unknown')
        text = payload.get('text', '')
        results.append(f'[Source: {source}; similarity={hit.score:.3f}; topic={topic}] {text}')
    return '\n'.join(results)
