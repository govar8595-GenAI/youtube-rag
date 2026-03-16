# YouTube Video Chat — Adaptive Multi-Source RAG

Chat with any YouTube video using AI. Ask questions and get answers pulled directly from the transcript — with automatic web search fallback when needed.

## Tech Stack

- **LangChain** — pipeline orchestration
- **OpenAI** — LLM + embeddings
- **FAISS** — vector store
- **yt-dlp** — transcript extraction
- **FastAPI** — REST API
- **Streamlit** — UI

## Project Structure
```
youtube-rag/
├── main.py
├── config.py
├── ingest_youtube.py
├── retriever.py
├── web_search.py
├── adaptive_router.py
├── rag_pipeline.py
├── streamlit_app.py
├── requirements.txt
├── .env.example
├── agents/
│   ├── query_classifier.py
│   └── evaluator.py
└── api/
    └── routes.py
```

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your `OPENAI_API_KEY` to `.env`

## Run
```bash
# Terminal 1 — API
uvicorn api.routes:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — UI
streamlit run streamlit_app.py
```

## How It Works

1. Paste a YouTube URL — transcript is fetched and chunked into a vector store
2. Ask a question — intent is classified automatically
3. Adaptive retrieval — transcript first, web search fallback if needed
4. Self-evaluation — confidence score and groundedness check on every answer
5. Answer returned with timestamps and source citations

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ingest` | Ingest a YouTube video |
| POST | `/chat` | Ask a question |
| GET | `/videos` | List indexed videos |
| GET | `/health` | Health check |