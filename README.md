# YouTube Video Chat — Adaptive Multi-Source RAG

A production-grade question-answering system that lets you chat with any YouTube video.  
Uses an **Adaptive Multi-Source RAG** architecture: retrieves from the video transcript first, automatically falls back to live web search when the transcript alone is insufficient.

---

## Architecture

```
User Query
    │
    ▼
Query Understanding Agent (LLM classifier)
    │
    ▼
Query Intent Classification
  video_specific | timestamp_lookup | conceptual | general | summarization
    │
    ▼
Adaptive Retrieval Router
    ├── Transcript Vector Store (FAISS / Chroma)   ← always tried first
    └── Web Search (Tavily / SerpAPI / DuckDuckGo) ← triggered when needed
    │
    ▼
Context Aggregation & Formatting
    │
    ▼
LLM Answer Generation (GPT-4o-mini / GPT-4o)
    │
    ▼
Self-Evaluation Agent (groundedness + completeness scores)
    │
    ▼
Optional Expanded Retrieval Loop
    │
    ▼
Structured Final Response
  { answer, sources, confidence, intent, evaluation }
```

---

## Project Structure

```
/project
├── main.py                  # FastAPI server entry point
├── config.py                # Env-driven configuration
├── ingest_youtube.py        # Transcript fetch + chunking
├── retriever.py             # FAISS / Chroma vector store + retrieval
├── web_search.py            # Multi-backend web search
├── adaptive_router.py       # Routing logic (transcript vs web)
├── rag_pipeline.py          # End-to-end pipeline orchestration
├── streamlit_app.py         # Optional Streamlit UI
├── example_queries.py       # CLI demo script
├── requirements.txt
├── .env.example
│
├── agents/
│   ├── query_classifier.py  # Intent classification agent
│   └── evaluator.py         # Self-evaluation / confidence agent
│
├── api/
│   └── routes.py            # FastAPI endpoints
│
└── vector_store/            # Auto-created; stores FAISS / Chroma indices
```

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (required)
# Add TAVILY_API_KEY for best web search results (optional but recommended)
```

### 3. Start the API server

```bash
python main.py
# Server runs at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### 4. Ingest a video

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "title": "My Video"}'
```

Response:
```json
{
  "video_id": "dQw4w9WgXcQ",
  "num_chunks": 47,
  "message": "Video 'My Video' ingested successfully with 47 chunks."
}
```

### 5. Chat with the video

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"video_id": "dQw4w9WgXcQ", "question": "What is the main topic of this video?"}'
```

Response:
```json
{
  "answer": "The video is about...",
  "sources": [
    {"type": "youtube", "timestamp": "00:32", "youtube_url": "..."},
    {"type": "web", "url": "https://...", "title": "..."}
  ],
  "confidence": "high",
  "intent": "video_specific_question",
  "retrieval_log": [...],
  "evaluation": {
    "groundedness_score": 0.9,
    "completeness_score": 0.85,
    "hallucination_risk": "low",
    "reasoning": "..."
  }
}
```

### 6. Run example queries (CLI)

```bash
python example_queries.py --url "https://www.youtube.com/watch?v=vo6aDcnPzCU"
```

### 7. Streamlit UI (optional)

```bash
# Start API first (step 3), then in another terminal:
streamlit run streamlit_app.py
```

---

## API Endpoints

| Method | Endpoint   | Description                          |
|--------|-----------|--------------------------------------|
| POST   | /ingest   | Ingest a YouTube video               |
| POST   | /chat     | Ask a question about an ingested video |
| GET    | /videos   | List all indexed videos              |
| GET    | /health   | Health check                         |

Full interactive docs: `http://localhost:8000/docs`

---

## Adaptive Retrieval Logic

| Query Intent           | Strategy |
|------------------------|----------|
| `video_specific_question` | Transcript-first → web fallback if thin |
| `timestamp_lookup`     | Transcript only (timestamps irrelevant on web) |
| `summarization`        | Extended transcript retrieval (2× top_k) |
| `conceptual_question`  | Transcript-first → web fallback if thin |
| `general_information`  | Hybrid: transcript + web always |

---

## Web Search Backends

The system auto-selects based on available API keys:

1. **Tavily** (recommended) — `TAVILY_API_KEY` → [tavily.com](https://tavily.com) free tier
2. **SerpAPI** — `SERPAPI_API_KEY` → [serpapi.com](https://serpapi.com)
3. **DuckDuckGo** — No key needed, automatic fallback

---

## Configuration Reference

| Variable               | Default              | Description |
|------------------------|----------------------|-------------|
| `OPENAI_API_KEY`       | *(required)*         | OpenAI API key |
| `LLM_MODEL`            | `gpt-4o-mini`        | Generation model |
| `EMBEDDING_MODEL`      | `text-embedding-3-small` | Embedding model |
| `VECTOR_STORE_BACKEND` | `faiss`              | `faiss` or `chroma` |
| `TOP_K`                | `5`                  | Docs to retrieve |
| `CHUNK_SIZE`           | `800`                | Chars per chunk |
| `CHUNK_OVERLAP`        | `150`                | Overlap between chunks |
| `TAVILY_API_KEY`       | *(optional)*         | Tavily web search |
| `SERPAPI_API_KEY`      | *(optional)*         | SerpAPI web search |

---

## Example Queries

```
# Video-specific
"What does the presenter say about transformers?"
"What tools are demonstrated in this video?"

# Timestamp lookup
"When does the speaker start talking about fine-tuning?"
"At what point is the demo shown?"

# Conceptual
"Can you explain the RAG concept mentioned in the video?"

# Summarization
"Give me the 5 key takeaways from this video."

# General (triggers web search)
"What are the latest benchmarks for GPT-4o?"
```
