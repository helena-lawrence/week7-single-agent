PHASE 5 — STUDYPILOT UI: CONTRAST & READABILITY FIX

This is a UI-only update to the previous StudyPilot professional Streamlit frontend.
It fixes illegible pale-on-white sidebar buttons, API badge text, resume-thread
controls, and improves chat readability. It does NOT change agent logic.

INSTALL ON WINDOWS
1. Back up your existing ai-study-agent\ui.py.
2. Copy ui.py from this ZIP into ai-study-agent\ui.py (replace it).
3. Merge the .streamlit folder into ai-study-agent\.streamlit.
4. Keep your original .env, api.py, agent_factory.py and Qdrant data.
5. Restart Streamlit: streamlit run ui.py
   (FastAPI must already be running: uvicorn api:app --reload --port 8000).
6. Hard refresh your browser (Ctrl+Shift+R).

NOTES
- The sidebar API badge should be dark text on a light mint background.
- Sidebar buttons should be white text on a dark indigo button.
- The summary and retrieval answer content comes from your agent; changing the
  UI doesn't fix inaccurate RAG answers or speed up local Ollama inference.
