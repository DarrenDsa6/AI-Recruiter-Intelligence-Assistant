# Migration Plan: Synchronous Recruiter -> Async Candidate Platform

## Summary

Pivot the AI Recruiter Intelligence Assistant from a synchronous, recruiter-facing tool
to an asynchronous, candidate-facing platform with persistent storage, email-based auth,
Redis Streams-backed job queue, pgvector embeddings, and a re-engineered UX flow.

---

## Architecture Comparison

| Layer            | Original                              | Current                                        |
|------------------|--------------------------------------|------------------------------------------------|
| **Auth**         | None                                 | Email OTP via Redis + JWT                     |
| **State**        | In-memory dict + ChromaDB            | PostgreSQL (users/reports) + pgvector (vectors)|
| **Queue**        | Synchronous `asyncio.gather`         | Redis Streams (producer/consumer groups)     |
| **Worker**       | None (in-request LLM calls)         | Separate `worker.py` process                  |
| **LLM Keys**     | User-supplied per request            | Backend shared key (env var)                  |
| **Frontend UX**  | Recruiter dashboard, sync wait/timeout | Candidate portal, async "queued" state      |
| **Email**        | None                                 | Resend (OTP + completion notification)        |
| **Storage**      | ChromaDB keyed by session_id        | PostgreSQL + pgvector keyed by resume_id      |
| **Session**      | In-memory dict                       | Redis-backed (survives restart, auto-expires) |
| **Chat**         | Resume-only RAG                      | Resume + JD + GitHub context with guardrails  |
| **Guardrails**   | None                                 | Injection detection, off-topic blocking, output sanitization |

---

## Phase 1: Infrastructure & Dependencies -- DONE

- `requirements.txt`: pgvector, redis, asyncpg, sqlalchemy, resend, pyjwt, prometheus, email-validator
- `.env.example`: All env vars configured
- `docker-compose.yml`: 3 services (backend, worker, frontend)

## Phase 2: Backend Storage & Session Overhaul -- DONE

- `services/db.py`: Engine + session factory + `CREATE EXTENSION vector` + `Base.metadata.create_all`
- `services/vector_store.py`: pgvector via SQLAlchemy, async methods requiring db session
- `services/session_store.py`: Redis-backed async session store
- `services/redis_client.py`: Async Redis client (Upstash or local)
- `models/user.py`, `resume.py`, `chunk.py`, `report.py`: SQLAlchemy models (4 tables)
- `schemas/`: auth.py, upload.py, match.py, report.py, chat.py, common.py

## Phase 3: API Routing Changes -- DONE

- `api/auth.py`: OTP request + verify + JWT
- `api/upload.py`: Auth + SHA-256 dedup + saves chunks to `resume_chunks`
- `api/match.py`: Redis Stream producer + 202 + reports endpoints
- `api/chat.py`: Auth + RAG + JD/GitHub context + guardrails + streaming
- `main.py`: Auth router, DB/Redis lifecycle, Prometheus, health checks

## Phase 4: Background Worker -- DONE

- `worker.py`: Redis Stream consumer with retry/backoff, async matcher/vector_store
- `services/matcher.py`: Async `compute_similarity` with chunk scoring, takes db session

## Phase 5: LLM Prompt Re-Engineering -- DONE

- `services/llm_service.py`: Config at init via env vars, career coach prompts, 3 LLM methods

## Phase 6: Frontend UI/UX Flow -- DONE

- `AuthPage.jsx`: OTP digit boxes, step indicator, resend cooldown
- `UploadPage.jsx`: 3-step wizard with progress bar, drag-drop
- `Dashboard.jsx`: Report history sidebar, SVG ring gauge, collapsible sections, chat
- `App.jsx`: Auth guard, guest guard, `/auth`, `/dashboard/:reportId` routes
- `api.js`: JWT injection, all API functions
- `useBackendStatus.js`: 30s polling

## Phase 7: Configuration & Deployment -- DONE

- `Dockerfile`: Python 3.11, torch CPU, requirements.txt
- `Procfile`: web + worker processes
- `render.yaml`: web + worker services

## Phase 8: pgvector Migration -- DONE

- Removed `chromadb` from requirements
- Added `ResumeChunk` model with `Vector(384)` column
- Updated all callers for async vector_store interface with db session
- Removed `chroma_resume_id` from `master_resumes` table
- Updated ARCHITECTURE.md SQL schema diagram

## Phase 9: Chat Context Enhancement -- DONE

- Added `report_id` to `ChatRequest` schema
- Chat fetches `tailoring_reports` to get `jd_text` + `github_analysis`
- System prompt includes JD context, GitHub context, and resume RAG context
- Updated `ChatSection.jsx` props: `{ resumeId, reportId, disabled }`

## Phase 10: Chat Guardrails -- DONE

- `services/guardrails.py`: Input validation + output sanitization
- Prompt injection detection (16 patterns)
- Off-topic keyword blocking (requires 2+ matches)
- Message length cap (2000 chars)
- Rate limiting (50 msgs/session/hour via Redis)
- Code block stripping (``` and `inline`)
- URL/link stripping from LLM output
- System prompt updated with strict rules

---

## Security Notes

1. LLM API key is server-side only (never sent to frontend)
2. JWT tokens stored in localStorage, validated on all protected endpoints
3. Rate limiting on OTP endpoints (3/email/5min, 10/IP/hr)
4. Rate limiting on chat (50 msgs/session/hour)
5. SHA-256 resume deduplication prevents re-processing
6. Chat guardrails: prompt injection detection, off-topic blocking, output sanitization
7. Input validation: message length cap, injection pattern matching
8. Output filtering: code blocks, URLs, markdown stripped from LLM responses

---

## Production-Grade Features Checklist

- [x] Redis-backed session store (survives restarts, auto-expires)
- [x] PostgreSQL + pgvector for persistent data AND embeddings
- [x] Redis Streams for async job processing
- [x] Email notifications via Resend (OTP + completion)
- [x] JWT authentication
- [x] OTP-based email verification
- [x] SHA-256 resume deduplication
- [x] Prometheus metrics (request latency, error rates, throughput)
- [x] Structured logging with correlation IDs
- [x] Health check endpoint (DB + Redis)
- [x] Graceful shutdown (DB pool, Redis connections)
- [x] Retry with exponential backoff in worker
- [x] Dead letter stream for failed jobs
- [x] Rate limiting on auth endpoints
- [x] Chat guardrails (injection, off-topic, output sanitization)
- [x] Chat rate limiting (50 msgs/session/hour)
- [x] JD + GitHub context in chat

---

## Files Summary

### New Files
- `backend/services/db.py` -- PostgreSQL connection + pgvector extension
- `backend/services/redis_client.py` -- Async Redis client
- `backend/services/guardrails.py` -- Input validation + output sanitization
- `backend/api/auth.py` -- OTP endpoints
- `backend/worker.py` -- Redis Stream consumer worker
- `backend/models/user.py`, `resume.py`, `chunk.py`, `report.py` -- SQLAlchemy models
- `backend/schemas/auth.py`, `upload.py`, `match.py`, `report.py`, `chat.py`, `common.py` -- Pydantic schemas
- `frontend/recruiter-ui/src/pages/AuthPage.jsx` -- Auth page

### Modified Files
- `backend/requirements.txt` -- pgvector, redis, asyncpg, sqlalchemy, resend, pyjwt
- `backend/services/vector_store.py` -- pgvector, async, requires db session
- `backend/services/session_store.py` -- Redis-backed async
- `backend/services/matcher.py` -- Async with db session
- `backend/services/llm_service.py` -- Career coach prompts, config at init
- `backend/api/upload.py` -- Auth, SHA-256 dedup, saves to resume_chunks
- `backend/api/match.py` -- Redis Stream producer, 202, reports endpoints
- `backend/api/chat.py` -- Auth, RAG, JD/GitHub context, guardrails, streaming
- `backend/api/github.py` -- Async vector_store with db session
- `backend/api/search.py` -- Async vector_store with db session
- `backend/api/session.py` -- Async vector_store with db session
- `backend/main.py` -- Auth router, DB init, health checks, graceful shutdown
- `backend/Dockerfile` -- Python 3.11, torch CPU
- `backend/Procfile` -- web + worker processes
- `docker-compose.yml` -- 3 services (backend, worker, frontend)
- `render.yaml` -- web + worker services
- `frontend/recruiter-ui/src/pages/UploadPage.jsx` -- 3-step wizard
- `frontend/recruiter-ui/src/pages/Dashboard.jsx` -- Report history, async flow
- `frontend/recruiter-ui/src/hooks/useBackendStatus.js` -- 30s polling
- `frontend/recruiter-ui/src/services/api.js` -- Auth functions, JWT injection
- `frontend/recruiter-ui/src/App.jsx` -- New routes, auth guard
- `frontend/recruiter-ui/src/components/ChatSection.jsx` -- resumeId + reportId props

### Deleted Files
- None -- `session_store.py` is rewritten, not deleted
