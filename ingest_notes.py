"""Create the independent study-notes collection and embed local notes.

Never recreates or deletes an existing Qdrant collection. Checks vector size.
"""
import json
from qdrant_client import models
from config import ROOT, QDRANT_COLLECTION
from qdrant_retriever import get_client, embedding_model


def main():
    notes = json.loads((ROOT / 'notes.json').read_text(encoding='utf-8'))
    texts = [f"{n['topic']}. {n['explanation']}" for n in notes]
    vectors = embedding_model().encode(texts)
    vector_size = len(vectors[0])
    client = get_client()
    if not client.collection_exists(QDRANT_COLLECTION):
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )
        print(f'Created Qdrant collection {QDRANT_COLLECTION} ({vector_size} dims).')
    else:
        # Be explicit about mismatched dimensions; never overwrite an existing collection.
        info = client.get_collection(QDRANT_COLLECTION)
        vector_config = info.config.params.vectors
        configured_size = getattr(vector_config, 'size', None)
        if configured_size is not None and configured_size != vector_size:
            raise ValueError(
                f'Collection dimensions {configured_size} != current embedding size {vector_size}. '
                'Use a new QDRANT_COLLECTION instead of overwriting existing data.'
            )
    points = [
        models.PointStruct(
            id=i + 1,
            vector=vectors[i].tolist(),
            payload={'text': texts[i], 'topic': notes[i]['topic'],
                     'source': f"notes.json#{notes[i]['topic']}"},
        )
        for i in range(len(notes))
    ]
    client.upsert(collection_name=QDRANT_COLLECTION, points=points, wait=True)
    print(f'Indexed {len(points)} study notes into {QDRANT_COLLECTION}.')

if __name__ == '__main__':
    main()
