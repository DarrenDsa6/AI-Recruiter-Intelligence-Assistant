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
Frontend sends session_id + job_description + github_username
        │
        ▼
Load resume chunks + embeddings from ChromaDB (by session_id)
        │
        ├─────────────────────────────────────┐
        ▼                                     ▼
  Deterministic Engine                  LLM Intelligence Layer
  ─────────────────────                 ─────────────────────
  Skill Extraction (JD)                 analyze_github_repos()
  JD Skill Classification               generate_candidate_report()
    (required vs optional)              generate_interview_questions()
  Semantic Skill Matching
    (bge-small-en-v1.5, threshold 0.9)       │
  Weighted Score Calculation                  │
    (70% skills + 30% doc similarity)         │
        │                                     │
        └──────────────┬──────────────────────┘
                       ▼
         Return structured JSON:
         { match, github, report, questions }
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
Build LLM messages:
  system (resume context) + history + user question
        │
        ▼
Stream tokens via SSE (data: {...} format)
        │
        ▼
Save user + assistant messages to session store
```

### 4. Session Cleanup

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
| **LLM** | Mistral Large 3 (675B) via NVIDIA API |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 |
| **Semantic Matching** | BAAI/bge-small-en-v1.5 |
| **Vector DB** | ChromaDB (persistent) |
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

*Built with FastAPI, React, ChromaDB, and NVIDIA LLMs.*
