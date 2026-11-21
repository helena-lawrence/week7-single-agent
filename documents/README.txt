AI Study Agent - PDF Knowledge Base
================================

These four original, beginner-friendly, text-based PDFs are ready for your RAG project.

INSTALLATION (Windows / PowerShell)

1. Extract the ZIP.
2. Copy the four PDF files into:
   C:\Users\helen\project\ds-october-2026-week7\ai-study-agent\documents\
3. Open VS Code PowerShell in the ai-study-agent project.
4. Run: Get-ChildItem .\documents\*.pdf
5. Ensure Qdrant is running.
6. Run: python ingest_pdfs.py
7. Run: python test_pdf_search.py "How does LangGraph checkpointing work?"
8. Check that the retrieved source includes LangGraph_State_and_Checkpointing.pdf and a page number.

Sample follow-up questions:
- What is RAG and why do we use chunks?
- Explain the difference between an embedding model and an LLM.
- Why does LangGraph use thread_id for checkpoints?
- What is the reason-act-observe loop in a single AI agent?

Important: These are generated educational notes, not official vendor manuals.
The PDF contents include further-reading links to official documentation.
All files contain selectable text (no OCR needed).
