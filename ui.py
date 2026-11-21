"""Phase 5: colourful Streamlit frontend for the existing AI Study Assistant.

This UI keeps agent orchestration, RAG, memory and tool execution in FastAPI.
It does NOT expose AGENT_API_KEY to the browser; requests run server-side.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from uuid import uuid4

import requests
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("AGENT_API_KEY", "")

st.set_page_config(
    page_title="StudyPilot • AI Study Studio",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Only decorative static HTML/CSS is inserted; user/model text is rendered with
# Streamlit widgets, not raw HTML, to avoid untrusted HTML injection.
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --ink: #182447; --soft: #626f91; --purple: #6944ed; --teal: #0bb5a4; }
html, body, [class*="css"], [data-testid="stApp"] { font-family: 'DM Sans', Arial, sans-serif; }
[data-testid="stAppViewContainer"] { background: radial-gradient(ellipse at 92% -10%, #e7dfff 0%, transparent 36%), radial-gradient(ellipse at 5% 45%, #e4f8f7 0%, transparent 29%), #f7f8fe; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #111b3d 0%, #1a2351 68%, #28215a 100%); }
/* Apply sidebar text colour only to static content. Avoid forcing white text
   onto Streamlit's white status, input, select and button backgrounds. */
[data-testid="stSidebar"] { color: #f4f5ff; }
[data-testid="stSidebar"] .brand,
[data-testid="stSidebar"] .brand-sub,
[data-testid="stSidebar"] .side-tag,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color: #e8edff !important; }
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] * { color: #c9d1ff !important; }
[data-testid="stSidebar"] .stButton button { background: rgba(255,255,255,.09); border: 1px solid rgba(255,255,255,.21); color: #fff; }
[data-testid="stSidebar"] .stButton button:hover { background: rgba(255,255,255,.18); border-color: #8bdff6; }
[data-testid="stSidebar"] input { color: #172144 !important; }
[data-testid="block-container"] { padding-top: 1.35rem; max-width: 1180px; }
h1, h2, h3 { font-family: 'Manrope', Arial, sans-serif; }
.brand { padding: 10px 0 7px; font-family: 'Manrope', sans-serif; font-size: 1.56rem; font-weight: 800; letter-spacing: -.04em; color: white; }
.brand-star { display:inline-block; color:#71eadf; font-size:1.8rem; margin-right:9px; }
.brand-sub { color: #b8c6e5; font-size: .82rem; line-height: 1.6; margin-bottom: 19px; }
.side-tag { color:#c3cbf5; font-size:.72rem; letter-spacing:.12em; font-weight:700; margin-top:15px; margin-bottom:9px; }
.hero { background: linear-gradient(115deg,#5142c8 0%, #6852e5 48%, #169fc2 100%); color:white; border-radius:23px; padding:31px 36px; box-shadow:0 16px 40px rgba(76,71,171,.20); margin-bottom:21px; position:relative; overflow:hidden; }
.hero:after { content:'✦'; position:absolute; font-size:10rem; line-height:1; right:20px; top:-32px; opacity:.11; pointer-events:none; }
.eyebrow { display:inline-block; color:#dceaff; letter-spacing:.15em; font-weight:800; font-size:.70rem; margin-bottom:9px; }
.hero h1 { color:white; margin:0 0 9px; font-size:clamp(1.6rem,3vw,2.5rem); letter-spacing:-.045em; font-weight:800; }
.hero p { color:#eff2ff; font-size:.97rem; margin:0; max-width:690px; line-height:1.65; }
.section-label { color:#27355a; font-weight:800; font-size:1.04rem; margin:15px 0 8px; }
.pill { display:inline-block; padding:5px 11px; border-radius:999px; background:#e5f9f5; color:#087e75; font-size:.78rem; font-weight:700; }
.small-label { color:#6e7697; font-size:.78rem; }
.main-caption { color:#74809e; font-size:.84rem; }
[data-testid="stMetric"] { background:white; border:1px solid #e5e8f8; border-radius:17px; padding:15px 18px; box-shadow:0 5px 17px rgba(23,34,78,.035); }
[data-testid="stMetricLabel"] { color:#687799 !important; }
[data-testid="stMetricValue"] { color:#23325b !important; font-family:'Manrope',sans-serif; font-weight:800; font-size:1.35rem !important; }
[data-testid="stChatMessage"] { border-radius:17px; border:1px solid #e6eafd; background:#fff; margin-bottom:10px; box-shadow:0 4px 15px rgba(30,46,107,.035); }
[data-testid="stChatMessage"] p { line-height:1.65; }
[data-testid="stChatInput"] { border-radius:16px; }
div.stButton > button[kind="secondary"] { border-radius:13px; border:1px solid #e0e4f5; color:#253661; background:white; box-shadow:0 3px 12px rgba(29,44,97,.045); font-weight:650; min-height:45px; }
div.stButton > button[kind="secondary"]:hover { border-color:#8e7bf0; color:#4c35bc; background:#f6f3ff; }
/* High-contrast sidebar controls: stop pale-on-white labels in widgets. */
[data-testid="stSidebar"] div.stButton > button[kind="secondary"],
[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:focus {
  color: #ffffff !important;
  background: #374288 !important;
  border: 1px solid #7886d2 !important;
  box-shadow: none !important;
  font-weight: 700 !important;
}
[data-testid="stSidebar"] div.stButton > button[kind="secondary"] p,
[data-testid="stSidebar"] div.stButton > button[kind="secondary"] span {
  color: #ffffff !important;
}
[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover {
  background: #4e57a8 !important;
  border-color: #b2bbff !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
  background: rgba(255,255,255,.075);
  border: 1px solid rgba(201,209,255,.28);
  border-radius: 12px;
  overflow: hidden;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary,
[data-testid="stSidebar"] [data-testid="stExpander"] summary * {
  color: #ffffff !important;
  background: transparent !important;
}
[data-testid="stSidebar"] [data-testid="stTextInput"] input,
[data-testid="stSidebar"] [data-baseweb="select"] [role="combobox"],
[data-testid="stSidebar"] [data-baseweb="select"] [role="combobox"] *,
[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] * {
  color: #1e2a50 !important;
}
[data-testid="stSidebar"] [data-testid="stTextInput"] input::placeholder {
  color: #647091 !important;
  opacity: 1;
}
[data-testid="stSidebar"] [data-testid="stCodeBlock"] code {
  color: #1e2a50 !important;
}
/* Neutral typography in the answer area. */
[data-testid="stChatMessage"] { padding: 1.1rem 1.25rem; }
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li { font-size: 1rem; line-height: 1.65; }
[data-testid="stExpander"] { border-radius:12px; }
.status-chip { border-radius:12px; padding:13px 15px; font-size:.89rem; font-weight:750; display:flex; gap:10px; align-items:center; margin-bottom:12px; }
.status-chip.connected { background:#dcfce9; border:1px solid #86efac; color:#14532d; }
.status-chip.offline { background:#fff4dd; border:1px solid #f9cd78; color:#713f12; }
[data-testid="stSidebar"] .status-chip.connected { color:#14532d !important; }
[data-testid="stSidebar"] .status-chip.offline { color:#713f12 !important; }

#MainMenu {visibility:hidden;} footer {visibility:hidden;}
@media(max-width:760px) { .hero{ padding:24px 21px; border-radius:16px; } [data-testid="block-container"]{padding-left:1rem;padding-right:1rem;} }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=10, show_spinner=False)
def api_online(url: str) -> bool:
    try:
        r = requests.get(f"{url}/health", timeout=2.5)
        return r.ok
    except requests.RequestException:
        return False


def fresh_thread() -> str:
    return uuid4().hex


def get_chat(thread_id: str) -> dict:
    return st.session_state.conversations[thread_id]


if "conversations" not in st.session_state:
    first_id = fresh_thread()
    st.session_state.conversations = {
        first_id: {"title": "New conversation", "messages": []}
    }
    st.session_state.active_thread = first_id
if "active_thread" not in st.session_state.conversations:
    st.session_state.active_thread = next(iter(st.session_state.conversations))
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


# Sidebar: simple session switching; back-end memory is persisted by thread_id.
with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-star">✦</span>StudyPilot</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Your AI-powered learning workspace<br/>One smart agent · Multiple tools</div>', unsafe_allow_html=True)

    online = api_online(API_URL)
    if online:
        st.markdown('<div class="status-chip connected">✅ &nbsp; API connected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-chip offline">⚠️ &nbsp; API offline — start FastAPI</div>', unsafe_allow_html=True)

    if st.button("＋  New conversation", use_container_width=True):
        tid = fresh_thread()
        st.session_state.conversations[tid] = {"title": "New conversation", "messages": []}
        st.session_state.active_thread = tid
        st.session_state.pending_prompt = None
        st.rerun()

    st.markdown('<div class="side-tag">CONVERSATIONS</div>', unsafe_allow_html=True)
    choices = list(reversed(list(st.session_state.conversations)))
    choice = st.selectbox(
        "Switch conversation",
        options=choices,
        index=choices.index(st.session_state.active_thread),
        format_func=lambda tid: f"{st.session_state.conversations[tid]['title'][:26]} · {tid[:5]}",
        label_visibility="collapsed",
    )
    if choice != st.session_state.active_thread:
        st.session_state.active_thread = choice
        st.session_state.pending_prompt = None
        st.rerun()

    with st.expander("Resume a saved thread"):
        entered_id = st.text_input("Thread ID", placeholder="Paste a previous thread ID", max_chars=80)
        if st.button("Open thread", use_container_width=True):
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", entered_id or ""):
                st.error("Use 1–80 letters, numbers, underscores or hyphens.")
            else:
                if entered_id not in st.session_state.conversations:
                    st.session_state.conversations[entered_id] = {"title": "Resumed thread", "messages": []}
                st.session_state.active_thread = entered_id
                st.session_state.pending_prompt = None
                st.rerun()

    st.markdown('<div class="side-tag">AGENT CAPABILITIES</div>', unsafe_allow_html=True)
    st.caption("🧮  Calculator & study planner")
    st.caption("📚  Qdrant PDF knowledge search")
    st.caption("🕓  Current time")
    st.caption("🧠  SQLite conversation memory")

    st.divider()
    st.caption("Session ID (keep this to resume saved memory):")
    st.code(st.session_state.active_thread, language=None)
    st.caption("Demo UI · One agent · Local development")


st.markdown(
    """<div class="hero">
      <div class="eyebrow">✦ YOUR AI LEARNING COMPANION</div>
      <h1>Learn smarter. Build confidently.</h1>
      <p>Ask about RAG, LangGraph, LLMs and agentic AI. Search your PDFs, calculate study time, and explore ideas with one tool-powered assistant.</p>
    </div>""",
    unsafe_allow_html=True,
)

active = get_chat(st.session_state.active_thread)
messages = active["messages"]
assistant_msgs = [m for m in messages if m["role"] == "assistant"]
tool_count = sum(len(m.get("tools", [])) for m in assistant_msgs)
last_ms = next((m.get("latency_ms") for m in reversed(assistant_msgs) if m.get("latency_ms") is not None), None)

c1, c2, c3 = st.columns(3, gap="medium")
with c1:
    st.metric("Conversation turns", sum(m["role"] == "user" for m in messages))
with c2:
    st.metric("Tool calls", tool_count)
with c3:
    st.metric("Last response", f"{last_ms / 1000:.1f}s" if last_ms is not None else "—")

if not messages:
    st.markdown('<div class="section-label">Start with a question</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-caption">Pick an example or type your own question below.</div>', unsafe_allow_html=True)
    suggestions = [
        ("📚 Explain RAG", "Explain RAG using my indexed PDFs and cite the source."),
        ("🧠 LangGraph memory", "How does LangGraph checkpointing work? Include the PDF filename and page."),
        ("🧮 Study calculator", "How many 45-minute sessions do I need for 10 hours of learning?"),
        ("⚙️ Agentic AI tools", "Explain how AI agents call tools using my study documents."),
    ]
    for start in (0, 2):
        left, right = st.columns(2, gap="medium")
        for column, (label, question) in zip((left, right), suggestions[start:start + 2]):
            with column:
                if st.button(label, key=f"suggest_{start}_{label}", use_container_width=True):
                    st.session_state.pending_prompt = question
                    st.rerun()

st.markdown('<div class="section-label">Conversation</div>', unsafe_allow_html=True)
if not messages:
    st.caption("Your discussion will appear here. The agent chooses tools based on the question.")

for message in messages:
    avatar = "🤖" if message["role"] == "assistant" else "👤"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            tool_calls = message.get("tools", [])
            if tool_calls:
                with st.expander(f"🔧 {len(tool_calls)} tool call(s) · View details"):
                    for call in tool_calls:
                        st.markdown(f"**{call.get('name', 'Tool')}**")
                        st.json(call.get("args", {}))
            ms = message.get("latency_ms")
            if ms is not None:
                st.caption(f"⏱ Response time: {ms / 1000:.1f}s")

question = st.chat_input("Ask anything about your AI study materials…", max_chars=2000)
if st.session_state.pending_prompt:
    question = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if question:
    messages.append({"role": "user", "content": question})
    if active["title"] == "New conversation":
        active["title"] = question[:46] + ("…" if len(question) > 46 else "")

    with st.chat_message("user", avatar="👤"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Thinking and checking tools…"):
            try:
                response = requests.post(
                    f"{API_URL}/chat",
                    json={"question": question, "thread_id": st.session_state.active_thread},
                    headers={"X-API-Key": API_KEY},
                    timeout=180,
                )
                response.raise_for_status()
                payload = response.json()
                answer = str(payload.get("answer") or "The agent returned an empty answer.")
                calls = payload.get("tools") or []
                if not isinstance(calls, list):
                    calls = []
                ms = payload.get("latency_ms")
                st.markdown(answer)
                if calls:
                    with st.expander(f"🔧 {len(calls)} tool call(s) · View details"):
                        for call in calls:
                            st.markdown(f"**{call.get('name', 'Tool')}**")
                            st.json(call.get("args", {}))
                if isinstance(ms, (int, float)):
                    st.caption(f"⏱ Response time: {ms / 1000:.1f}s")
                messages.append({
                    "role": "assistant", "content": answer, "tools": calls,
                    "latency_ms": ms if isinstance(ms, (int, float)) else None,
                })
                st.rerun()
            except requests.Timeout:
                st.error("The request timed out. The model may be running slowly; check the FastAPI terminal.")
            except requests.HTTPError as exc:
                code = exc.response.status_code if exc.response is not None else "unknown"
                if code == 401:
                    st.error("API key mismatch. Check AGENT_API_KEY in your .env file and restart FastAPI and Streamlit.")
                else:
                    st.error(f"The API returned HTTP {code}. Check the FastAPI terminal for details.")
            except (requests.ConnectionError, requests.RequestException):
                st.error("Could not reach FastAPI. Start it with: uvicorn api:app --reload --port 8000")
            except (ValueError, TypeError):
                st.error("Unexpected API response. Inspect the FastAPI terminal output.")

st.markdown(
    '<div class="main-caption" style="margin:24px 0 4px;text-align:center">✦ StudyPilot · AI answers should be checked against cited sources</div>',
    unsafe_allow_html=True,
)
