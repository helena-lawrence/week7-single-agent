from tools import calculate, estimate_study_sessions, get_current_time, search_study_notes


def test_calculate():
    assert '3000' in calculate.invoke({'a': 250, 'b': 12, 'operation': 'multiply'})
    assert 'Cannot divide by zero' in calculate.invoke({'a': 5, 'b': 0, 'operation': 'divide'})


def test_study_sessions():
    assert '14 sessions' in estimate_study_sessions.invoke({'total_hours': 10, 'minutes_per_session': 45})


def test_time():
    assert '(Europe/London)' in get_current_time.invoke({'timezone': 'Europe/London'})


def test_keyword_search():
    from config import RETRIEVAL_MODE
    if RETRIEVAL_MODE == 'keyword':
        assert 'Source:' in search_study_notes.invoke({'query': 'RAG'})
