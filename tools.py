"""Phase 1 and 2: three original tools plus a custom study-planning tool.

Phase 3: switch search_study_notes from keyword search to Qdrant using .env.
"""
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from math import ceil
import json
from langchain.tools import tool
from config import ROOT, RETRIEVAL_MODE

@tool
def calculate(a: float, b: float, operation: Literal['add', 'subtract', 'multiply', 'divide']) -> str:
    """Do arithmetic with two numbers: add, subtract, multiply or divide."""
    if operation == 'add':
        answer = a + b
    elif operation == 'subtract':
        answer = a - b
    elif operation == 'multiply':
        answer = a * b
    else:
        if b == 0:
            return 'Cannot divide by zero.'
        answer = a / b
    return f'Result: {answer:g}'

@tool
def get_current_time(timezone: str = 'Europe/London') -> str:
    """Get the real current date and time for an IANA timezone such as Europe/London."""
    try:
        return datetime.now(ZoneInfo(timezone)).strftime('%A, %d %B %Y at %H:%M') + f' ({timezone})'
    except (ZoneInfoNotFoundError, ValueError):
        return 'Unknown timezone; try Europe/London.'

@tool
def estimate_study_sessions(total_hours: float, minutes_per_session: int = 45) -> str:
    """Estimate how many study sessions are needed to cover total_hours of learning."""
    if total_hours <= 0 or total_hours > 1000:
        return 'Provide study hours greater than zero and at most 1000.'
    if minutes_per_session < 5 or minutes_per_session > 240:
        return 'Session length must be between 5 and 240 minutes.'
    sessions = ceil(total_hours * 60 / minutes_per_session)
    return f'{total_hours:g} hours requires about {sessions} sessions of {minutes_per_session} minutes.'

@tool
def search_study_notes(query: str) -> str:
    """Search grounded local AI study notes about RAG, LangGraph, tool calling, agents and MCP."""
    if RETRIEVAL_MODE == 'qdrant':
        # Lazy import: the basic agent runs without installing embedding packages.
        from qdrant_retriever import query_notes
        return query_notes(query)
    if RETRIEVAL_MODE != 'keyword':
        return 'Unsupported RETRIEVAL_MODE. Choose keyword or qdrant.'
    notes = json.loads((ROOT / 'notes.json').read_text(encoding='utf-8'))
    q = query.casefold()
    matches = [
        f"[Source: notes.json / {n['topic']}] {n['explanation']}"
        for n in notes
        if any(k.casefold() in q for k in n['keywords'])
    ]
    return '\n'.join(matches[:4]) if matches else 'No matching note found in the local knowledge base.'

BASE_TOOLS = [calculate, get_current_time, search_study_notes, estimate_study_sessions]
