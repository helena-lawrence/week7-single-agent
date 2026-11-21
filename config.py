"""Shared settings; no credentials are hard-coded."""
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
DATA_DIR = ROOT / 'data'
DATA_DIR.mkdir(exist_ok=True)

LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama').strip().lower()
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:3b')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
AWS_REGION = os.getenv('AWS_REGION', 'eu-west-2')
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', '')
RETRIEVAL_MODE = os.getenv('RETRIEVAL_MODE', 'keyword').strip().lower()
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY', '')
QDRANT_COLLECTION = os.getenv('QDRANT_COLLECTION', 'ai_study_notes')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
CHECKPOINT_DB = DATA_DIR / 'checkpoints.sqlite'
PREFERENCE_DB = DATA_DIR / 'preferences.sqlite'
API_KEY = os.getenv('AGENT_API_KEY', '')
