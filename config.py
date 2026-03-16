import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# ── Vector Store ────────────────────────────────────────────────────────────
VECTOR_STORE_BACKEND: str = os.getenv("VECTOR_STORE_BACKEND", "faiss")   # "faiss" | "chroma"
VECTOR_STORE_DIR: str = os.getenv("VECTOR_STORE_DIR", "vector_store")

# ── Retrieval ────────────────────────────────────────────────────────────────
TOP_K: int = int(os.getenv("TOP_K", "5"))

# ── Web Search ───────────────────────────────────────────────────────────────
# Provide ONE of the three keys below:
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
# DuckDuckGo needs no key — used as fallback

# ── Text Splitting ────────────────────────────────────────────────────────────
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))

# ── Self-Evaluation ───────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))
