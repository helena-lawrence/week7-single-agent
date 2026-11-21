"""Index text-based PDFs from documents/ into the existing Qdrant collection.

- Retains all previously indexed notes.json points.
- Keeps PDF filename and 1-based page number as citation metadata.
- Uses deterministic UUID IDs so re-running updates existing chunks.
- Does not OCR scanned/image-only PDFs.
"""
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from pypdf import PdfReader
from qdrant_client import models

from config import ROOT, QDRANT_COLLECTION
from qdrant_retriever import get_client, embedding_model

DOCUMENTS_DIR = ROOT / 'documents'
CHUNK_SIZE = 900        # Characters, not tokens
CHUNK_OVERLAP = 150    # Characters
BATCH_SIZE = 32


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Create overlapping chunks without splitting in the middle of a word when possible."""
    if not 0 <= overlap < chunk_size:
        raise ValueError('overlap must be >= 0 and smaller than chunk_size')
    text = ' '.join(text.split())
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            space = text.rfind(' ', start + chunk_size // 2, end)
            if space > start:
                end = space
        chunk = text[start:end].strip()
        if chunk:
            yield chunk
        if end == len(text):
            break
        start = max(start + 1, end - overlap)


def pdf_chunks(pdf_path: Path):
    """Extract chunks and source metadata. Images/scanned pages are skipped."""
    reader = PdfReader(pdf_path)
    rel = pdf_path.relative_to(DOCUMENTS_DIR).as_posix()
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ''
        if not text.strip():
            print(f'  Skipping page {page_number} of {rel}: no extractable text')
            continue
        for chunk_index, text_chunk in enumerate(split_text(text)):
            # Use a UUID string (valid Qdrant point ID), separate from notes' integer IDs.
            point_id = str(uuid5(NAMESPACE_URL, f'ai-study-pdf:{rel}:page:{page_number}:chunk:{chunk_index}'))
            yield {
                'id': point_id,
                'text': text_chunk,
                'source': f'{rel}, page {page_number}',
                'source_file': rel,
                'page': page_number,
                'chunk_index': chunk_index,
                'topic': pdf_path.stem,
                'doc_type': 'pdf',
            }


def main():
    DOCUMENTS_DIR.mkdir(exist_ok=True)
    pdf_files = sorted(DOCUMENTS_DIR.rglob('*.pdf'))
    if not pdf_files:
        print(f'No PDFs found in {DOCUMENTS_DIR}. Add a PDF and retry.')
        return

    model = embedding_model()
    dim = len(model.encode('Dimension check').tolist())
    client = get_client()
    if not client.collection_exists(QDRANT_COLLECTION):
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )
        print(f'Created collection {QDRANT_COLLECTION} ({dim} dimensions).')
    else:
        params = client.get_collection(QDRANT_COLLECTION).config.params.vectors
        existing_dim = getattr(params, 'size', None)
        if existing_dim is not None and existing_dim != dim:
            raise ValueError(
                f'Qdrant collection uses {existing_dim} dimensions, but this model makes {dim}. '
                'Keep the original EMBEDDING_MODEL or choose a new QDRANT_COLLECTION.'
            )

    count = 0
    for pdf_path in pdf_files:
        try:
            chunks = list(pdf_chunks(pdf_path))
        except Exception as exc:
            print(f'Could not read {pdf_path.name}: {exc}')
            continue
        if not chunks:
            print(f'No extractable text in {pdf_path.name} (a scanned PDF may need OCR).')
            continue

        for offset in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[offset:offset+BATCH_SIZE]
            vectors = model.encode([x['text'] for x in batch], show_progress_bar=False)
            points = []
            for chunk, vector in zip(batch, vectors):
                payload = {k: v for k, v in chunk.items() if k != 'id'}
                points.append(models.PointStruct(
                    id=chunk['id'], vector=vector.tolist(), payload=payload
                ))
            client.upsert(collection_name=QDRANT_COLLECTION, points=points, wait=True)
        count += len(chunks)
        print(f'Indexed {pdf_path.name}: {len(chunks)} chunks')

    print(f'Done: indexed {count} PDF chunks in collection {QDRANT_COLLECTION}.')
    print('Existing notes.json points were not deleted.')
    print('If you shorten or remove a PDF, old extra chunks may remain until you delete them.')


if __name__ == '__main__':
    main()
