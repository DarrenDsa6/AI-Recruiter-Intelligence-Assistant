# AI Resume Tailor

An asynchronous, candidate-facing platform that analyzes resumes against job descriptions. Upload a PDF resume and paste a job description, and receive an ATS compatibility score, skill gap analysis, actionable rewrites, and interview prep questions -- all powered by career coach AI. Authentication is email OTP only. Job processing runs in the background via Redis Streams.

---

## Features

- **Email OTP Authentication** -- Passwordless sign-in via 6-digit code (Resend email)
- **Resume Ingestion** -- PDF upload with SHA-256 deduplication; parsed, chunked, and embedded into ChromaDB keyed by resume_id (persists across applications)
- **Async Job Queue** -- Redis Streams producer/consumer pattern; jobs are submitted instantly (202) and processed in a separate worker
- **ATS Compatibility Scoring** -- Deterministic skill matching (semantic + regex) at 70% weight + document similarity at 30%
- **Career Coach AI** -- Re-engineered LLM prompts focus on ATS optimization, not recruiter judgment
- **Actionable Rewrites** -- AI generates rewritten bullet points for weak resume sections
- **Gap-Focused Interview Prep** -- Questions target the candidate's exact skill gaps with prep tips
- **Report History** -- All past analyses persist in PostgreSQL with a sidebar dashboard
- **Streaming Chat** -- Resume-aware conversational follow-ups with RAG context
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

  UploadPage ──► POST /api/upload ───► SHA-256 dedup check ──► ChromaDB (embeddings)
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
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, React Router 7, Tailwind CSS 3 |
| **Backend** | FastAPI, Python 3.11, Uvicorn |
| **Auth** | Email OTP (Redis) + JWT (PyJWT) |
| **Queue** | Redis Streams (Upstash) |
| **Database** | PostgreSQL (Supabase/Neon) via SQLAlchemy + asyncpg |
| **Vector DB** | ChromaDB (persistent, keyed by resume_id) |
| **LLM** | Shared backend API key via AsyncOpenAI |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 |
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
│   │   ├── match.py             # POST /api/match/:id/start, GET /api/reports
│   │   ├── chat.py              # POST /api/chat (RAG, auth)
│   │   ├── github.py            # GitHub data ingestion
│   │   └── search.py            # Semantic search
│   ├── models/
│   │   ├── user.py              # SQLAlchemy: users
│   │   ├── resume.py            # SQLAlchemy: master_resumes
│   │   └── report.py            # SQLAlchemy: tailoring_reports
│   ├── schemas/
│   │   ├── auth.py, upload.py, match.py, report.py, chat.py, common.py
│   ├── services/
│   │   ├── db.py                # Engine + async session factory
│   │   ├── redis_client.py      # Async Redis client (Upstash REST)
│   │   ├── session_store.py     # Redis-backed conversation history
│   │   ├── vector_store.py      # ChromaDB (resume_id keyed)
│   │   ├── matcher.py           # Deterministic scoring engine
│   │   ├── llm_service.py       # Career coach prompts, 3 LLM methods
│   │   ├── parser.py            # PDF/DOCX text extraction
│   │   ├── chunker.py           # Text chunking
│   │   ├── embedding_service.py # Embedding generation
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
│   ├── Procfile
│   └── docker-compose.yml
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
├── render.yaml
├── MIGRATION_PLAN.md
└── ARCHITECTURE.md
```

---

## Running Locally

### Prerequisites

- Python 3.11+, Node.js 18+
- Upstash Redis (free tier)
- Supabase or Neon PostgreSQL (free tier)
- Resend API key (free tier)

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in all env vars
uvicorn main:app --reload --port 8000
```

### Worker (separate terminal)

```bash
cd backend
python worker.py
```

### Frontend

```bash
cd frontend/recruiter-ui
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### Docker Compose (all services)

```bash
docker compose up --build
```

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_CONNECTION_STRING` | PostgreSQL connection URL |
| `UPSTASH_REDIS_REST_URL` | Upstash Redis REST URL |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis REST token |
| `LLM_API_KEY` | Shared backend LLM API key |
| `JWT_SECRET` | Secret for signing JWT tokens |
| `RESEND_API_KEY` | Resend email API key |
| `RESEND_FROM_EMAIL` | Verified sender email |
| `GITHUB_TOKEN` | (Optional) GitHub API token for higher rate limits |

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
- SHA-256 resume deduplication prevents re-processing

---

## Author

**Darren Dsa** - [GitHub](https://github.com/DarrenDsa6)
