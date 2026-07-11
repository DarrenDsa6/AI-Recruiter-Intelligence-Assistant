# Architecture

> AI Resume Tailor -- an asynchronous, candidate-facing platform for resume tailoring with email OTP auth, Redis Streams job queue, and career coach AI.

---

## Data Flow

### 1. Authentication

```
User enters email
        │
        ▼
POST /api/auth/request-otp
        │
        ├── Generate 6-digit code
        ├── Store in Redis: otp:{email} (TTL 300s)
        ├── Rate limit: otp_rate:{email} (3/5min), otp_ip:{ip} (10/hr)
        └── Send via Resend email
        │
        ▼
User enters code
        │
        ▼
POST /api/auth/verify-otp
        │
        ├── Compare against Redis key
        ├── Upsert user in PostgreSQL
        └── Return JWT token
        │
        ▼
Frontend stores JWT in localStorage
All subsequent requests include Authorization: Bearer <jwt>
```

### 2. Resume Upload

```
User uploads PDF + pastes JD
        │
        ▼
POST /api/upload (authenticated)
        │
        ├── Calculate SHA-256 of file bytes
        ├── Query PostgreSQL: master_resumes WHERE user_id + file_hash
        │
        ├── EXISTS? ──► Return existing resume_id (skip processing)
        │
        └── NEW? ─────► Parser → Chunker → Embedder → ChromaDB
                         │
                         ├── Insert into master_resumes
                         └── Return { resume_id, filename, skills }
```

### 3. Job Submission (Async)

```
POST /api/match/:upload_id/start (authenticated)
        │
        ├── Create tailoring_reports row (status: "pending")
        ├── Push to Redis Stream "tailoring-jobs":
        │     { report_id, user_id, resume_id, jd_text }
        │
        └── Return 202 Accepted { report_id, status: "pending" }

    ┌─────────────────────────────────────────────────┐
    │              Redis Stream                        │
    │   tailoring-jobs ──────► tailoring-workers       │
    │   (producer: API)      (consumer: worker.py)     │
    └─────────────────────────────────────────────────┘
                        │
                        ▼
              Worker picks up job
```

### 4. Background Processing (worker.py)

```
Worker starts, connects to Redis + PostgreSQL
        │
        ▼
XREADGROUP from "tailoring-jobs" (blocks 5s)
        │
        ▼
process_job(payload):
        │
        ├── Update report status → "processing"
        │
        ├── Pull resume chunks from ChromaDB (by resume_id)
        │
        ├── matcher.compute_similarity(chunks, jd)
        │     ├── Extract JD skills (regex + classifier)
        │     ├── Semantic matching (all-MiniLM-L6-v2, threshold 0.8)
        │     └── Weighted score: (skill × 0.7) + (doc_sim × 0.3)
        │
        ├── llm_service.generate_candidate_report(resume, jd, match_result)
        │     └── Career coach prompt → ATS score, gaps, rewrites
        │
        ├── llm_service.generate_interview_questions(resume, jd, match_result)
        │     └── Gap-focused questions with prep tips
        │
        ├── llm_service.generate_actionable_rewrites(chunks, jd, match_result)
        │     └── Rewritten bullet points for weak sections
        │
        ├── Save all results to PostgreSQL (status → "completed")
        │
        ├── Send email via Resend with link to dashboard
        │
        └── XACK message from Redis Stream

    On failure:
        ├── Retry with exponential backoff (3 attempts: 1s, 2s, 4s)
        └── Dead letter stream after all retries exhausted
```

### 5. Report Retrieval

```
Dashboard mounts → GET /api/reports
        │
        └── List all reports for authenticated user (PostgreSQL)

Dashboard polls → GET /api/reports/:report_id
        │
        ├── status == "pending" / "processing" → show spinner, keep polling (3s)
        ├── status == "failed" → show error
        └── status == "completed" → render full results:
              ├── ATS Compatibility Score (circular gauge)
              ├── Summary
              ├── Strengths / Gaps / Recommendations
              ├── Actionable Rewrites (rewritten bullets)
              ├── Interview Questions (gap-focused)
              └── Career Coach Chat (RAG over resume chunks)
```

### 6. Follow-Up Chat

```
User types question
        │
        ▼
POST /api/chat (authenticated)
        │
        ├── Load resume chunks from ChromaDB (by resume_id from report)
        ├── Load conversation history from Redis session store
        ├── Embed query (all-MiniLM-L6-v2)
        ├── Retrieve top-5 relevant chunks (cosine similarity)
        ├── Build LLM messages: system (RAG context) + history + question
        │
        └── Stream response via SSE
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

## Key Design Decisions

1. **Candidate-facing, not recruiter-facing.** The UX is designed for job seekers optimizing their own resumes. LLM prompts frame feedback as a career coach, not a gatekeeper.

2. **Async job queue via Redis Streams.** Jobs are submitted instantly (202 Accepted) and processed in a separate worker. This decouples the API from slow LLM calls and allows the worker to scale independently.

3. **Resume_id keying with SHA-256 dedup.** ChromaDB embeddings are keyed by resume_id (not session_id). If a user uploads the same PDF again, the existing embeddings are reused -- no re-processing.

4. **Two-layer scoring.** Deterministic skill matching (semantic + regex) provides consistent, explainable results. The LLM layer adds ATS-aware analysis, rewrites, and interview prep on top.

5. **Redis-backed session store.** Conversation history for chat is stored in Redis with TTL. Survives server restarts, shared between FastAPI and worker, auto-expires.

6. **Email OTP only (no passwords).** Simpler auth flow, no password storage, no reset flows. Rate limiting on OTP endpoints prevents abuse.

7. **Error-resilient rendering.** All LLM-driven data passes through `renderItem` helpers with `toList` guards. Handles inconsistent LLM output formats (strings, objects, arrays) without crashing.

8. **Model pre-warming.** The embedding model loads during FastAPI lifespan startup, not on first request. Eliminates 20-40s cold-start delay.

---

## Production Features

- Redis-backed session store (survives restarts, auto-expires)
- PostgreSQL for persistent user/report data
- Redis Streams for async job processing with consumer groups
- Email notifications via Resend (OTP + job completion)
- JWT authentication with rate limiting
- SHA-256 resume deduplication
- Prometheus metrics (request latency, error rates, throughput)
- Health check endpoint with DB + Redis connectivity checks
- Graceful shutdown (DB pool, Redis connections)
- Retry with exponential backoff in worker (3 attempts)
- Dead letter stream for failed jobs
- Docker Compose for local development (backend + worker + frontend)

---

*Built with FastAPI, React, ChromaDB, Redis Streams, and career coach AI.*
