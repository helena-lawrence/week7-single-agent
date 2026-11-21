"""Factory that switches providers and keeps SQLite checkpoints open."""
from contextlib import contextmanager
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver
from config import (LLM_PROVIDER, OLLAMA_MODEL, OLLAMA_BASE_URL, AWS_REGION,
                    BEDROCK_MODEL_ID, CHECKPOINT_DB)
from tools import BASE_TOOLS
from memory_tools import create_memory_tools

PROMPT = """
You are an AI Study Assistant.

Rules:
1. For questions about study notes, use search_study_notes.
2. Answer using the retrieved information.
3. Include source references returned by the tool.
4. Never invent source names or citations.
5. If the retrieved information is insufficient,
   clearly state that.
6. Explain everything in simple English.
"""


def get_model():
    if LLM_PROVIDER == 'ollama':
        from langchain_ollama import ChatOllama
        return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
    if LLM_PROVIDER == 'bedrock':
        if not BEDROCK_MODEL_ID:
            raise ValueError('Set BEDROCK_MODEL_ID in .env to an approved model/profile identifier.')
        from langchain_aws import ChatBedrockConverse
        return ChatBedrockConverse(model=BEDROCK_MODEL_ID, region_name=AWS_REGION)
    raise ValueError('LLM_PROVIDER must be ollama or bedrock.')


@contextmanager
def open_agent(user_id: str = 'local-demo'):
    # SqliteSaver is intended for local learning / low-concurrency usage.
    with SqliteSaver.from_conn_string(str(CHECKPOINT_DB)) as checkpointer:
        agent = create_agent(
            model=get_model(),
            tools=BASE_TOOLS + create_memory_tools(user_id),
            system_prompt=PROMPT,
            checkpointer=checkpointer,
        )
        yield agent
