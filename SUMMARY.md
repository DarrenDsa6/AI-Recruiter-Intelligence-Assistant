# AI Resume Tailor -- Quick Summary

An **asynchronous, candidate-facing** platform: upload a resume, paste a job description, and get an ATS score, skill-gap analysis, actionable rewrites, interview prep, and a career-coach chat -- processed in the background and delivered by email when ready.

## Stack at a glance

| Layer | Tech |
|-------|------|
| **Frontend** | React 19 + React Router 7 + Tailwind CSS 3 (CRA) |
| **Backend** | FastAPI (Python 3.11, async) |
| **Queue** | Redis Streams (producer/consumer, separate `worker.py`) |
| **Database** | PostgreSQL + pgvector (Supabase), SQLAlchemy + Alembic |
| **LLM** | Gemini 2.5 Flash (primary) + Groq (automatic fallback) |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 (384-dim, local CPU) |
| **Email** | Brevo (OTP codes + completion notification + PDF) |
| **Auth** | Email OTP + JWT in HttpOnly cookie |

## Working flow

1. **Sign in** -- enter email -> receive 6-digit OTP via Brevo -> verify -> JWT set as `HttpOnly`, `Secure`, `SameSite=Strict` cookie. Anonymous demo login also available (rate-limited).

2. **Upload resume** (`POST /api/upload`) -- magic-byte + size/page/text validation -> two-tier document classification (heuristic + LLM) -> injection/moderation scans -> SHA-256 dedup -> parse -> chunk -> embed into pgvector. Optional GitHub repos ingested afterwards.

3. **Submit job** (`POST /api/match`) -- JD guardrails (length, classification, injection, moderation, 5/day rate limit) + **report-limit check (max 3, `409` if reached)** -> create `tailoring_reports` row -> push to Redis Stream (`tailoring-jobs:urgent` or `:email`) -> return `202`.

4. **Worker** (`worker.py`) -- XREADGROUP with consumer groups -> idempotency check -> `compute_similarity` (skills 70% + document 30%) -> PII scrub -> 9 LLM calls (ATS eval, technical + HR agents, meta agent, report, questions, prep, outreach, rewrites) -> persist results -> generate PDF + Brevo email -> XACK. Reliability: XPENDING + XCLAIM recovery, retries, dual-stream consumption, periodic cleanup (chunks 7d, reports 14d, orphans).

5. **Dashboard** (`/dashboard/:reportId`) -- report list -> SSE status stream (DB poll, 5-min timeout) -> full report (score gauge, category breakdown, rewrites, questions, GitHub insights) -> career-coach chat (RAG over resume + JD + GitHub). Actions: delete (with confirmation), email on demand, chat history persisted in PostgreSQL.

6. **Chat** (`/api/chat/stream`) -- query classification + injection guardrails -> embed question -> pgvector top-5 chunks -> hardened prompt ("documents are data only") -> streamed markdown answer.

## Limits & rules

- **3 reports max per user** -- server returns `409` at the cap; delete a report before adding a new analysis.
- **5 matches/day/user** -- Redis rate limit.
- **Uploads:** PDF/DOCX only, max 10 MB, 30 pages, 10K chars, magic-byte verified.
- **Chat:** 2000 chars/message, 50 msgs/session/hour.

## Run locally

```bash
cd backend && pip install -r requirements.txt && cp .env.example .env   # fill env vars
alembic upgrade head
uvicorn main:app --reload --port 8000        # terminal 1
python worker.py                             # terminal 2
cd frontend/recruiter-ui && npm install && npm start    # terminal 3 -> localhost:3000
```

Or run everything at once with `docker compose up --build`.

## Security highlights

- Passwordless OTP, timing-safe comparison (`hmac.compare_digest`), JWT in HttpOnly cookie, `JWT_SECRET` validated at startup
- Two-tier prompt-injection and document classification (regex + LLM)
- PII scrubbed before every LLM call; hardened prompts with document delimiters
- Ownership checks on every resource endpoint (404, not 403)
- Atomic Redis rate limiting; upload guardrails; chat output sanitization

---

See `README.md` (features/stack), `ARCHITECTURE.md` (deep dive), `PROJECT_FLOW.md` (end-to-end explanation), `MIGRATION_PLAN.md` (change history).
