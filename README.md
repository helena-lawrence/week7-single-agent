# AI Study Assistant — Enhanced Single-Agent Project

This **keeps one LangChain agent** and extends the original `ai-study-agent-starter.zip` through eight phases. Use **Windows + VS Code + PowerShell + Python 3.12**. It follows the initial LangChain Agents & Memory Lab; Qdrant, Bedrock, Langfuse, Streamlit and FastAPI are **new project extensions**.

## Project map

| File | Purpose |
|---|---|
| `main.py` | CLI chat (Phases 1–4) |
| `tools.py` | Calculator, time, sample notes, study sessions (Phases 1–2) |
| `ingest_notes.py`, `qdrant_retriever.py` | Embed notes and retrieve vectors (Phase 3) |
| `agent_factory.py`, `memory_tools.py` | LLM switching, SQLite checkpoint and preferences (Phases 4 & 6) |
| `api.py`, `ui.py` | FastAPI service and Streamlit frontend (Phases 5 & 8) |
| `trace_helpers.py`, `evaluate.py`, `golden_questions.json` | Tracing and basic tool-coverage evaluation (Phase 7) |
| `.env.example` | Local settings template, no secrets |
| `Dockerfile`, `compose.yaml` | API container build and local Qdrant |

## Phase 1 — Run the base agent (three tools)

**1.** Unzip and open `ai-study-agent-enhanced` in VS Code. Open PowerShell in this folder.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
ollama pull llama3.2:3b
ollama list
python main.py --thread-id study-001
```

If activation is blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then retry activation. If PowerShell can't find Ollama, install and start it. If the model is weak at tool calling, switch to `qwen2.5:7b` in `.env` if your machine can run it.

Ask **each** question and check the printed `[Tool]` call:
- `What is 250 multiplied by 12?` → `calculate`
- `What time is it in London?` → `get_current_time`
- `Explain RAG from my study notes.` → `search_study_notes`

The code *registers six tools* across all phases (three core tools, one custom tool, two memory tools); the first three questions concentrate on your original tools.

## Phase 2 — Add and test one custom tool

Open `tools.py` and locate `estimate_study_sessions`:

```python
@tool
def estimate_study_sessions(total_hours: float, minutes_per_session: int = 45) -> str:
    """Estimate how many study sessions are needed to cover total_hours of learning."""
    ...
```

It is already registered in `BASE_TOOLS` at the bottom of `tools.py`. Ask:

`I need 10 hours of study. How many 45-minute study sessions is that?`

Expected numeric result: **14 sessions**. The trace should include `estimate_study_sessions`. Edit the tool's docstring and compare how frequently the LLM chooses it. A genuinely new fifth domain tool can be added with `@tool` and appended to `BASE_TOOLS`.

## Phase 3 — Replace keyword retrieval with Qdrant vector search

**1.** Install vector requirements (these may download large machine-learning dependencies):

```powershell
python -m pip install -r requirements-rag.txt
```

**2.** Start Qdrant. If you already have Qdrant at `localhost:6333`, reuse it and do **not** start another copy. Otherwise:

```powershell
docker compose up -d qdrant
```

**3.** Open `.env` and change `RETRIEVAL_MODE=keyword` to `RETRIEVAL_MODE=qdrant`. Keep `QDRANT_COLLECTION=ai_study_notes`. This is a new collection; it does **not** overwrite your existing RAG project's collection.

**4.** Create embeddings and upsert `notes.json` into the collection:

```powershell
python ingest_notes.py
```

The default embedding model is `sentence-transformers/all-MiniLM-L6-v2`. The first use downloads its weights. Always embed queries and indexed documents using the **same model**. If you change embedding models, create a new named Qdrant collection.

**5.** Test retrieval with:

```powershell
python main.py --thread-id qdrant-001
```

Ask `What does LangGraph do? Search the study notes and show the source.` Check that `search_study_notes` calls Qdrant and provides `[Source: notes.json#LangGraph]` or similar grounded evidence.

This is *real semantic retrieval*, but only over five tiny sample notes. Later replace `notes.json` with extracted/chunked PDFs and adjust ingestion, without changing the surrounding agent.

## Phase 4 — Persist memory between restarts

The agent has a `SqliteSaver` checkpoint in `data/checkpoints.sqlite`. It stores conversation state by `thread_id`. Test:

1. Run `python main.py --thread-id memory-001`.
2. Ask `For this conversation, I am learning LangGraph first.`
3. Exit. Re-run `python main.py --thread-id memory-001`.
4. Ask `What subject did I say I am learning first?`

The answer should reference LangGraph. Use `--thread-id memory-002` to demonstrate a separate conversation.

You also have a distinct `data/preferences.sqlite` for explicit *long-term* preferences. Ask `Remember that I prefer short Python examples for AI lessons.` The agent can call `save_study_preference`. Later ask `What learning preferences do you remember?`; it can call `read_study_preferences`. These demos are **not** a production privacy or security solution. Do **not** save personal secrets, API keys or sensitive information.

For a production multi-user service, replace this local SQLite approach with durable, shared storage and proper user authentication/authorization.

## Phase 5 — Streamlit chat UI backed by FastAPI

Install UI/API packages:

```powershell
python -m pip install -r requirements-api.txt
```

In `.env`, replace `AGENT_API_KEY=replace-with-a-long-random-string` with a unique random key. You can generate one using:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Open **Terminal A** and run:

```powershell
uvicorn api:app --reload --port 8000
```

Open **Terminal B**, activate the same `.venv`, then run:

```powershell
streamlit run ui.py
```

Visit `http://localhost:8501`, type a question, and verify that the UI shows both the answer and any tool names. To test the API directly, use a PowerShell request:

```powershell
$headers = @{ "X-API-Key" = "PUT_YOUR_LOCAL_AGENT_API_KEY_HERE" }
$body = @{ question = "What is 9 times 8?"; thread_id = "demo-api-1" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/chat" -Headers $headers -ContentType "application/json" -Body $body
```

For a browser-only test, `http://localhost:8000/docs` shows the OpenAPI interface; calling `/chat` requires the `X-API-Key` header.

## Phase 6 — Change Ollama to Amazon Bedrock

Keep everything else. Install:

```powershell
python -m pip install -r requirements-aws.txt
aws sts get-caller-identity
aws bedrock list-foundation-models --region eu-west-2 --query "modelSummaries[].{Name:modelName,ID:modelId}" --output table
aws bedrock list-inference-profiles --region eu-west-2 --output table
```

Ask your administrator which *model ID or inference profile ID* you may invoke. Catalogue visibility is not the same as invocation permission. In `.env`:

```dotenv
LLM_PROVIDER=bedrock
AWS_REGION=eu-west-2
BEDROCK_MODEL_ID=YOUR_APPROVED_MODEL_OR_PROFILE_ID
```

Run `python main.py --thread-id bedrock-001`. `agent_factory.py` uses `ChatBedrockConverse` instead of `ChatOllama`. Leave embedding generation separate; the sample Qdrant implementation still uses a local Sentence Transformers embedding model.

Bedrock model calls can incur AWS charges. Use your configured AWS credential chain locally; **never** put company AWS access keys in `.env`, source code, screenshots or Git. Some Bedrock models do not support tool calling; choose one that does.

## Phase 7 — Langfuse tracing + evaluation

Install:

```powershell
python -m pip install -r requirements-observability.txt
```

If approved by your organisation, set the three Langfuse environment variables in `.env` and rerun the agent. `trace_helpers.py` adds the Langfuse v3 LangChain callback to each agent invocation. It can capture prompts, outputs and tool details, so **do not** send sensitive internal data to an unapproved Langfuse tenant.

Evaluate the tool-selection benchmark:

```powershell
python evaluate.py
```

The included `golden_questions.json` contains four expected-tool test cases. The program prints actual tools, approximate latency and reported token counts. Tool selection coverage **does not prove that an answer is correct**. Manually inspect groundedness/citations, and later add safety, hallucination and human-graded tests.

The API additionally exposes Prometheus metrics at `/metrics`, protected by the same demo API key.

## Phase 8 — Docker, FastAPI and deployment toward AWS ECS

The FastAPI app is in `api.py`. For local Docker packaging, use:

```powershell
docker build -t ai-study-agent:1.0 .
```

The image uses `requirements-prod.txt`, which installs all integrations and is larger than the local CLI setup. For Docker-on-Windows plus local Ollama, see below. API memory is **not durable on AWS Fargate** unless you attach/configure persistent storage. You must replace SQLite checkpoints with a shared production database (e.g. PostgreSQL) before scaling to several workers/tasks.

**Recommended AWS architecture:**

`Streamlit or other frontend → HTTPS load balancer → ECS Fargate FastAPI task → Bedrock LLM + reachable Qdrant service → production checkpoint store → CloudWatch / Langfuse`

**Deployment steps:**

1. Securely configure a Bedrock-enabled IAM **task role** (separate from the ECS **task execution role**).
2. Create an ECR repository in `eu-west-2`, build and push the API Docker image.
3. Create ECS cluster/service/task definition, VPC, security groups and HTTPS load balancer.
4. Store the demo key and other secrets in AWS Secrets Manager; for production implement actual sign-in rather than a single shared API key.
5. Provide a persistent vector database and a durable checkpoint backend. Your laptop's `localhost:6333` and Ollama are not reachable from ECS.
6. Set task configuration to `LLM_PROVIDER=bedrock`, `BEDROCK_MODEL_ID=...`, and `QDRANT_URL=...` as appropriate.
7. Test the public `/health` endpoint, authenticated `/chat`, logs and alerts.
8. Add CI/CD, access controls, rate limits, request size controls, timeouts, prompt-injection tests and autoscaling as follow-up production work.

**Do not call the included Dockerfile production-ready.** It is a learning deployment scaffold. In particular, a single-worker SQLite-based agent will not scale horizontally without substantial storage/authentication changes.

## Optional: Docker run against Ollama on Windows

If Ollama is running on your Windows host and Docker Desktop can reach it, run:

```powershell
docker run --rm -p 8000:8000 --env-file .env -e OLLAMA_BASE_URL=http://host.docker.internal:11434 -v "${PWD}/data:/app/data" ai-study-agent:1.0
```

**Important:** the container also needs a reachable Qdrant URL if `RETRIEVAL_MODE=qdrant`. For simple testing, set `RETRIEVAL_MODE=keyword` first. Some Ollama host configurations require enabling access from Docker Desktop; use the Ollama documentation and restrict network exposure.

## Tests and troubleshooting

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

| Problem | What to check |
|---|---|
| `ModuleNotFoundError` | Is `.venv` active and the relevant `requirements-*.txt` installed? |
| Ollama connection error | Is Ollama running and the model pulled? |
| Qdrant `collection not found` | Is Docker/Qdrant running? Did `python ingest_notes.py` succeed? |
| Qdrant dimension mismatch | Keep embedding model consistent or create a **new** Qdrant collection. |
| API 401 | Did both server and Streamlit use exactly the same `AGENT_API_KEY`? |
| Bedrock AccessDenied | Check permissions, region, model access and invocation profile with your admin. |
| No Langfuse traces | Are the Langfuse vars correctly set? Is remote tracing authorised? |
| Unexpected model tool use | The small Ollama model may not call tools reliably. Try a stronger tool-capable model. |

**Security reminders:** `compose.yaml` publishes Qdrant only on local loopback. Do not expose unauthenticated Qdrant or the demo API to the public internet. Never commit `.env`; avoid committing `data/*.sqlite`. Verify that all outside inputs and retrieved text are treated as untrusted content.

## Official references

- [LangChain create_agent](https://docs.langchain.com/oss/python/langchain/agents)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Qdrant quickstart](https://qdrant.tech/documentation/quickstart/)
- [Langfuse + LangChain integration](https://langfuse.com/integrations/frameworks/langchain)
- [AWS Bedrock Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)
- [AWS ECS task IAM roles](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)

For the staging prerequisites, Qdrant provisioning, Service Connect wiring, and
CI deployment sequence, see [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md). These are
deployment instructions; AWS resources have not been provisioned by this guide.
