# AI Recruiter Intelligence Assistant

> An end-to-end AI-powered candidate screening platform that analyzes resumes against job descriptions using LLMs, semantic search, and structured skill matching.

---

## Architecture Overview

![alt text](Gemini_Generated_Image_t1wl4dt1wl4dt1wl.png)

---

## Data Flow

### 1. Resume Ingestion (`POST /api/upload`)

```
User uploads PDF/DOCX
        │
        ▼
Parser Service ──► extract raw text
        │
        ▼
Skill Extraction ──► detect skills via regex + alias map (skills.json)
        │
        ▼
Chunker Service ──► split into 500-char windows (50-char overlap)
        │
        ▼
Embedder Service ──► all-MiniLM-L6-v2 → vector embeddings
        │
        ▼
Vector Store ──► ChromaDB (keyed by session_id)
        │
        ▼
Return session_id to frontend
```

### 2. Match Analysis (`POST /api/match`)

```
Frontend sends session_id + job_description + github_username + github_token
        │
        ▼
Load resume chunks + embeddings from ChromaDB (by session_id)
        │
        ├─────────────────────────────────────┐
        ▼                                     ▼
  Deterministic Engine                  LLM Intelligence Layer (async)
  ─────────────────────                 ───────────────────────────
  Skill Extraction (JD)                 1. analyze_github_repos()
  JD Skill Classification               2. generate_candidate_report() ┐
    (required vs optional)              3. generate_interview_questions() ┘ parallel via asyncio.gather
  Semantic Skill Matching
    (all-MiniLM-L6-v2, threshold 0.8)   All LLM calls use AsyncOpenAI
  Weighted Score Calculation            (non-blocking, event loop
    (70% skills + 30% doc similarity)    serves other requests during
        │                                network I/O)
        │                                     │
        └──────────────┬──────────────────────┘
                       ▼
         Return structured JSON:
         { match, github, report, questions }

GitHub Token: supplied via frontend input or GITHUB_TOKEN env var.
GitHubService creates an authenticated requests.Session when a token is present,
enabling higher API rate limits and access to private repositories.
```

### 3. Follow-Up Chat (`POST /api/chat/stream`)

```
User types question
        │
        ▼
Load resume context from ChromaDB
Load conversation history from session store
        │
        ▼
Embed user query (all-MiniLM-L6-v2)
        │
        ▼
Retrieve top-5 relevant chunks via ChromaDB vector search (cosine similarity)
(if no results, falls back to full resume text)
        │
        ▼
Build LLM messages:
  system (RAG context) + history + user question
        │
        ▼
Stream tokens via SSE (data: {...} format)
        │
        ▼
Save user + assistant messages to session store
```

The frontend ChatSection features a **full-screen popup mode** - clicking the expand
icon opens the chat as a centered overlay at 95vw × 90vh with a dark backdrop.

### 4. Model Pre-Warming (Startup)

```
Server starts
        │
        ▼
lifespan() runs before accepting requests
        │
        ├── Pre-warm embedding model (run_in_executor)
        │     all-MiniLM-L6-v2 → loaded into memory
        │     First user request is instant, no download delay
        │
        ├── Start session cleanup background worker
        │
        ▼
Ready to serve requests
```

### 5. Session Cleanup

```
Manual:   DELETE /api/session/end/{id}  →  erase ChromaDB + session store
Auto:     Background worker every 60s   →  expire sessions older than 1 hour
```

---

## Scoring Formula

```
final_score = (skill_score × 0.7) + (document_score × 0.3)

skill_score = (required_match × 0.7) + (optional_match × 0.3)

document_score = cosine_similarity(JD_embedding, resume_embedding)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, React Router 7, Tailwind CSS 3, Framer Motion |
| **Backend** | FastAPI, Python 3.11, Uvicorn |
| **LLM** | Configurable (OpenAI, NVIDIA, Together, Groq, DeepSeek) |
| **Embeddings / Semantic Matching** | sentence-transformers/all-MiniLM-L6-v2 (single model) |
| **Vector DB** | ChromaDB (in-memory) |
| **LLM Calls** | Async via AsyncOpenAI (non-blocking, parallel) |
| **PDF Export** | html2canvas-pro + jsPDF |
| **Markdown Rendering** | react-markdown + remark-gfm |
| **File Parsing** | PyMuPDF (PDF), python-docx (DOCX) |
| **External APIs** | GitHub REST API |

---

## Project Structure

```
AI-Recruiter-Intelligence-Assistant/
├── backend/
│   ├── main.py                  # FastAPI app entrypoint
│   ├── api/
│   │   ├── upload.py            # Resume ingestion
│   │   ├── match.py             # Structured + streaming match
│   │   ├── chat.py              # Follow-up chat streaming
│   │   ├── session.py           # Session management
│   │   ├── github.py            # GitHub data ingestion
│   │   └── search.py            # Semantic search
│   ├── services/
│   │   ├── parser.py            # PDF/DOCX text extraction
│   │   ├── chunker.py           # Text chunking
│   │   ├── embedding_service.py # Embedding generation + cache
│   │   ├── vector_store.py      # ChromaDB operations
│   │   ├── session_store.py     # In-memory session + chat history
│   │   ├── skills.py            # Regex-based skill extraction
│   │   ├── semantic_matcher.py  # Semantic skill matching
│   │   ├── weighted_skill_gap_analyzer.py  # Scoring engine
│   │   ├── jd_skill_classifier.py  # Required vs optional
│   │   ├── matcher.py           # Orchestrator
│   │   ├── llm_service.py       # LLM API client
│   │   ├── github_service.py    # GitHub API client
│   │   ├── explainer.py         # Score explanation
│   │   └── skill_embedding_cache.py  # Precomputed embeddings
│   └── data/
│       ├── skills.json           # Skill dictionary
│       └── skill_aliases.json    # Normalization map
│
├── frontend/recruiter-ui/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── UploadPage.jsx    # Resume + JD input
│   │   │   └── Dashboard.jsx     # Results + chat
│   │   ├── components/
│   │   │   ├── ScoreGauge.jsx    # Circular SVG gauge
│   │   │   ├── SkillsSection.jsx # Skill tag clouds
│   │   │   ├── GithubSection.jsx # GitHub insights
│   │   │   ├── ReportSection.jsx # AI report cards
│   │   │   ├── QuestionsSection.jsx  # Accordion questions
│   │   │   └── ChatSection.jsx   # Markdown chat
│   │   └── utils/
│   │       └── pdfGenerator.js   # PDF export
│   └── tailwind.config.js
```

---

## Key Design Decisions

1. **Two-layer architecture**: Deterministic scoring (skills, embeddings) provides consistent, explainable results, while the LLM layer adds intelligent reasoning, GitHub analysis, and question generation.

2. **Session isolation**: Each resume upload creates a unique session. All vectors in ChromaDB are tagged with `session_id`, making deletion atomic and complete.

3. **Streaming chat**: Follow-up conversations use SSE streaming with persistent context. The full conversation history is stored in-memory per session and injected into every LLM call.

4. **Skill normalization**: A curated `skill_aliases.json` maps variations (e.g., "JS" → "JavaScript") for consistent matching. Semantic matching catches synonyms via embeddings.

5. **PDF export**: The report can be downloaded as a pixel-perfect A4 PDF capturing all styled components exactly as rendered.

6. **Error-resilient rendering**: All LLM-driven array data (strengths, weaknesses, signals, recommendations, questions, skills) passes through a `renderItem` helper with a `toList` guard. This handles the LLM's inconsistent output formats - whether it returns strings, objects, or arrays - without crashing or showing raw JSON. Supported object shapes include `{category, details, skills, projects}`, `{signal, evidence}`, `{project, skills, details}`, `{status, next_steps, justification}`, and flat `{name, description, text}` fallbacks.

7. **Authenticity score normalization**: The LLM may return `authenticity_score` on either a 0-10 or 0-100 scale. The frontend normalizes values > 10 by dividing by 10 before display.

8. **Async LLM calls**: All LLM interactions use `AsyncOpenAI` with `asyncio.gather` for parallel execution. Report generation and interview questions run concurrently, cutting total match time from ~24s to ~16s. The event loop remains free to handle other requests during network I/O.

9. **Model pre-warming**: The embedding model is loaded during `lifespan()` startup before the first request arrives. This prevents a 20-40s cold-start delay on the first user's request. Render free tier services still spin down after 15 min idle, but a free UptimeRobot ping every 10 min keeps the instance alive.

10. **Frontend retry logic**: The Dashboard auto-retries failed match requests up to 2 times with a 10s delay. This handles Render cold starts gracefully - the server wakes up, loads the model, and responds on the retry.

---

## Running Locally

```bash
# Backend
cd backend
.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000

# Frontend
cd frontend/recruiter-ui
npm start
```

Open [http://localhost:3000](http://localhost:3000) to use the application.

---

*Built with FastAPI, React, ChromaDB, and async LLM inference.*
