"""Shared runner: one question per invocation, tool use trace and latency."""
from time import perf_counter
from trace_helpers import get_callbacks


def ask(agent, question: str, thread_id: str, user_id: str = 'local-demo') -> dict:
    callbacks = get_callbacks()
    started = perf_counter()
    result = agent.invoke(
        {'messages': [{'role': 'user', 'content': question}]},
        config={
            'configurable': {'thread_id': f'{user_id}:{thread_id}'},
            'recursion_limit': 18,
            'callbacks': callbacks,
            'metadata': {'langfuse_user_id': user_id, 'langfuse_session_id': thread_id},
        },
    )
    messages = result['messages']
    last_user = max(i for i, m in enumerate(messages) if m.type == 'human')
    recent = messages[last_user + 1:]
    calls = []
    token_count = 0
    for msg in recent:
        if getattr(msg, 'tool_calls', None):
            calls.extend([{'name': t['name'], 'args': t['args']} for t in msg.tool_calls])
        usage = getattr(msg, 'usage_metadata', None) or {}
        token_count += usage.get('total_tokens', 0) or 0
    content = messages[-1].content
    answer = content if isinstance(content, str) else str(content)
    return {
        'answer': answer,
        'tools': calls,
        'latency_ms': round((perf_counter() - started) * 1000),
        'tokens_reported': token_count or None,
        'thread_id': thread_id,
    }
