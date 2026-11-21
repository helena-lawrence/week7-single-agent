"""Phase 8: educational single-API-key FastAPI service.

Production requires OIDC auth, authorization, throttling and durable shared storage.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from secrets import compare_digest
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from config import API_KEY
from agent_factory import open_agent
from agent_runner import ask
from trace_helpers import flush_traces

REQUESTS = Counter('study_agent_requests_total', 'Requests to agent', ['status'])
LATENCY = Histogram('study_agent_request_seconds', 'Duration of agent calls')


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not API_KEY or API_KEY == 'replace-with-a-long-random-string':
        raise RuntimeError('Set a unique AGENT_API_KEY in .env before starting the API.')
    with open_agent(user_id='api-demo') as agent:
        app.state.agent = agent
        yield
    flush_traces()


app = FastAPI(title='AI Study Agent', lifespan=lifespan)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    thread_id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/metrics')
def metrics(x_api_key: str = Header(default='')):
    if not compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail='Invalid API key')
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post('/chat')
def chat(request: ChatRequest, x_api_key: str = Header(default='')):
    if not compare_digest(x_api_key, API_KEY):
        REQUESTS.labels(status='unauthorized').inc()
        raise HTTPException(status_code=401, detail='Invalid API key')
    with LATENCY.time():
        try:
            answer = ask(app.state.agent, request.question, request.thread_id, user_id='api-demo')
            REQUESTS.labels(status='ok').inc()
            return answer
        except Exception:
            REQUESTS.labels(status='error').inc()
            # Do not disclose API internals to callers.
            raise HTTPException(status_code=500, detail='Agent execution failed; check server logs.')
