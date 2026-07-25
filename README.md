# AI Resume Tailor

An asynchronous, candidate-facing platform that analyzes resumes against job descriptions. Upload a PDF resume and paste a job description, and receive an ATS compatibility score, skill gap analysis, actionable rewrites, and interview prep questions -- all powered by career coach AI. Authentication is email OTP only. Job processing runs in the background via Redis Streams.

---

## Features

- **Email OTP Authentication** -- Passwordless sign-in via 6-digit code (Resend email)
- **Resume Ingestion** -- PDF upload with SHA-256 deduplication; parsed, chunked, and embedded into PostgreSQL via pgvector (persists across applications)
- **Async Job Queue** -- Redis Streams producer/consumer pattern; jobs are submitted instantly (202) and processed in a separate worker
- **ATS Compatibility Scoring** -- Deterministic skill matching (semantic + regex) at 70% weight + document similarity at 30%
- **Career Coach AI** -- Re-engineered LLM prompts focus on ATS optimization, not recruiter judgment
- **Actionable Rewrites** -- AI generates rewritten bullet points for weak resume sections
- **Gap-Focused Interview Prep** -- Questions target the candidate's exact skill gaps with prep tips
- **Report History** -- All past analyses persist in PostgreSQL with a sidebar dashboard
- **Streaming Chat** -- Resume-aware conversational follow-ups with JD + GitHub context via RAG
- **Chat Guardrails** -- Input validation, prompt injection protection, output sanitization, rate limiting
- **PDF Export** -- Download the full report as a pixel-perfect A4 PDF
- **Background Worker** -- Separate process with retry/backoff, dead letter stream, and email notifications

---

## Architecture

```
Candidate (Browser)                    Backend (FastAPI)                 Infrastructure
─────────────────                    ─────────────────                 ──────────────
  AuthPage ──► request-otp ──────────► Redis (store OTP, 5min TTL)
              verify-otp ────────────► Postgres (upsert user)
              ◄── JWT token ──────────

  UploadPage ──► POST /api/upload ───► SHA-256 dedup check ──► PostgreSQL + pgvector (embeddings)
                 POST /api/match ────► Redis Stream ────────► Worker consumes
                 ◄── 202 Accepted ────                    ┌───────────────────────┐
                                                          │  1. compute_similarity │
                                                          │  2. LLM report         │
                                                          │  3. LLM rewrites       │
                                                          │  4. LLM questions      │
                                                          │  5. Save to Postgres   │
                                                          │  6. Send email (Resend)│
                                                          └───────────────────────┘

  Dashboard ──► GET /api/reports ────► Postgres (list reports)
                GET /api/reports/:id ─► Postgres (full report)
                Poll status until "completed"
                POST /api/chat ──────► Guardrails → RAG → LLM → Stream
                                       (JD + resume + GitHub context)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, React Router 7, Tailwind CSS 3 |
| **Backend** | FastAPI, Python 3.11, Uvicorn |
| **Auth** | Email OTP (Redis) + JWT (PyJWT) |
| **Queue** | Redis Streams (Upstash) |
| **Database** | PostgreSQL (Supabase) via SQLAlchemy + asyncpg |
| **Vector DB** | PostgreSQL + pgvector (resume_chunks table) |
| **LLM** | NVIDIA API (mistralai/mistral-medium-3.5-128b) via AsyncOpenAI |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 (384 dimensions) |
| **Email** | Resend |
| **Metrics** | Prometheus (prometheus-fastapi-instrumentator) |
| **PDF Export** | html2canvas-pro + jsPDF |
| **Parsing** | PyMuPDF (PDF), python-docx (DOCX) |

---

## Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI app, CORS, DB/Redis lifecycle, Prometheus
│   ├── worker.py                # Redis Stream consumer (separate process)
│   ├── api/
│   │   ├── auth.py              # POST /api/auth/request-otp, verify-otp
│   │   ├── upload.py            # POST /api/upload (auth + SHA-256 dedup)
│   │   ├── match.py             # POST /api/match, GET /api/reports
│   │   ├── chat.py              # POST /api/chat/stream (RAG + guardrails + JD/GitHub context)
│   │   ├── github.py            # GitHub data ingestion
│   │   ├── search.py            # Semantic search
│   │   └── session.py           # Session management
│   ├── models/
│   │   ├── user.py              # SQLAlchemy: users
│   │   ├── resume.py            # SQLAlchemy: master_resumes
│   │   ├── chunk.py             # SQLAlchemy: resume_chunks (pgvector)
│   │   └── report.py            # SQLAlchemy: tailoring_reports
│   ├── schemas/
│   │   ├── auth.py, upload.py, match.py, report.py, chat.py, common.py
│   ├── services/
│   │   ├── db.py                # Engine + async session factory + pgvector extension
│   │   ├── redis_client.py      # Async Redis client (Upstash or local)
│   │   ├── session_store.py     # Redis-backed conversation history
│   │   ├── vector_store.py      # PostgreSQL + pgvector (resume_chunks table)
│   │   ├── matcher.py           # Deterministic scoring engine
│   │   ├── llm_service.py       # Career coach prompts, 3 LLM methods
│   │   ├── guardrails.py        # Input validation, injection detection, output sanitization
│   │   ├── parser.py            # PDF/DOCX text extraction
│   │   ├── chunker.py           # Text chunking
│   │   ├── embedding_service.py # Embedding generation
│   │   ├── model_registry.py    # Model loading + caching
│   │   ├── skills.py            # Regex skill extraction
│   │   ├── semantic_matcher.py  # Semantic skill matching
│   │   ├── weighted_skill_gap_analyzer.py
│   │   ├── jd_skill_classifier.py
│   │   ├── github_service.py    # GitHub API client
│   │   └── explainer.py         # Score explanation
│   ├── data/                    # skills.json, skill_aliases.json
│   ├── requirements.txt
│   ├── .env.example
│   ├── Dockerfile
│   └── Procfile
│
├── frontend/recruiter-ui/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── AuthPage.jsx     # Email OTP sign-in
│   │   │   ├── UploadPage.jsx   # 3-step wizard (input -> processing -> queued)
│   │   │   └── Dashboard.jsx    # Report history, results, chat
│   │   ├── components/
│   │   │   ├── ScoreGauge.jsx, SkillsSection.jsx, ReportSection.jsx
│   │   │   ├── QuestionsSection.jsx, ChatSection.jsx, Loader.jsx
│   │   ├── hooks/
│   │   │   └── useBackendStatus.js
│   │   ├── services/
│   │   │   └── api.js           # Auth + API client with JWT injection
│   │   └── utils/
│   │       └── pdfGenerator.js
│   ├── Dockerfile
│   └── nginx.conf
│
├── docker-compose.yml
├── render.yaml
├── MIGRATION_PLAN.md
└── ARCHITECTURE.md
```

---

## Running Locally

### Prerequisites

- Python 3.11+, Node.js 18+
- Supabase account (PostgreSQL + pgvector)
- Upstash account (Redis)
- Resend account (email)
- NVIDIA API key (LLM)

### 1. Set up environment

```bash
cd backend
cp .env.example .env   # fill in all env vars
```

### 2. Backend

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Worker (separate terminal)

```bash
python worker.py
```

### 4. Frontend (separate terminal)

```bash
cd frontend/recruiter-ui
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### Docker Compose

```bash
docker compose up --build
```

---

## Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_CONNECTION_STRING` | PostgreSQL connection URL (Supabase) | `postgresql+asyncpg://...` |
| `UPSTASH_REDIS_REST_URL` | Upstash Redis REST URL | `https://...` |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis REST token | `AXxx...` |
| `LLM_API_KEY` | NVIDIA API key | `nvapi-...` |
| `LLM_BASE_URL` | LLM provider base URL | `https://integrate.api.nvidia.com/v1` |
| `LLM_MODEL` | Model name | `mistralai/mistral-medium-3.5-128b` |
| `JWT_SECRET` | Secret for signing JWT tokens | 64-char hex string |
| `RESEND_API_KEY` | Resend email API key | `re_...` |
| `RESEND_FROM_EMAIL` | Verified sender email | `noreply@yourdomain.com` |
| `GITHUB_TOKEN` | (Optional) GitHub API token | `ghp_...` |

---

## Deployment

### Render

1. Push to GitHub and connect to [Render](https://render.com).
2. `render.yaml` defines two services: `web` (FastAPI) and `worker` (Python).
3. Set all environment variables in the Render dashboard.
4. Free tier: add an UptimeRobot ping to `/health` every 10 min.

### Vercel (Frontend)

1. Connect `frontend/recruiter-ui` to [Vercel](https://vercel.com).
2. Set `VITE_API_URL` to your backend URL.
3. Deploy.

---

## Security

- LLM API key is server-side only (never sent to frontend)
- JWT tokens stored in localStorage, validated on all protected endpoints
- Rate limiting on OTP endpoints (3/email/5min, 10/IP/hr)
- Rate limiting on chat (50 messages/session/hour)
- SHA-256 resume deduplication prevents re-processing
- Chat guardrails: prompt injection detection, off-topic blocking, output sanitization
- Input validation: message length cap (2000 chars), injection pattern matching
- Output filtering: code blocks, URLs, and markdown stripped from LLM responses

---

## Author

**Darren Dsa** - [GitHub](https://github.com/DarrenDsa6)
