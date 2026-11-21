# Phase 2: PDF ingestion for your existing AI Study Assistant

These are additive files for the existing project. Do not delete `ingest_notes.py` or the existing Qdrant collection.

1. Copy `ingest_pdfs.py`, `test_pdf_search.py`, and `qdrant_retriever.py` into the existing `ai-study-agent` folder. The new `qdrant_retriever.py` differs only by making the score threshold configurable and giving a clearer no-results message. Alternatively, add only those lines to your current working version.
2. Create a `documents` folder and copy at least one **text-based** PDF into it.
3. Activate `.venv`, run `python -m pip install pypdf`, and make sure Docker Qdrant is available at `http://localhost:6333`.
4. In `.env`: `RETRIEVAL_MODE=qdrant`, `QDRANT_COLLECTION=ai_study_notes`, `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`, and optionally `RAG_SCORE_THRESHOLD=0.30`.
5. Run `python ingest_pdfs.py`.
6. Run `python test_pdf_search.py`, then `python main.py --thread-id pdf-001`.
7. Ask a question whose answer is clearly in the PDF. Check the source filename and page number in the retrieval tool output.

Notes: `pypdf` cannot OCR image-only PDFs. Re-ingesting a modified PDF updates matching chunk IDs, but may leave old surplus chunks if you shortened or removed pages. This is a learning-grade ingestion script, not a production document synchronisation pipeline.
