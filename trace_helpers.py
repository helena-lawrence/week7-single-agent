"""Phase 7: optional Langfuse LangChain v3 callback tracing."""
import os


def get_callbacks():
    if not (os.getenv('LANGFUSE_PUBLIC_KEY') and os.getenv('LANGFUSE_SECRET_KEY')):
        return []
    from langfuse.langchain import CallbackHandler
    return [CallbackHandler()]


def flush_traces():
    if os.getenv('LANGFUSE_PUBLIC_KEY') and os.getenv('LANGFUSE_SECRET_KEY'):
        from langfuse import get_client
        get_client().flush()
