# Migration Plan: Synchronous Recruiter -> Async Candidate Platform

## Summary

Pivot the AI Recruiter Intelligence Assistant from a synchronous, recruiter-facing tool
to an asynchronous, candidate-facing platform with persistent storage, email-based auth,
Redis Streams-backed job queue, pgvector embeddings, multi-layer security, Brevo email integration, and a re-engineered UX flow.

---

## Architecture Comparison

| Layer            | Original                              | Current                                        |
|------------------|--------------------------------------|------------------------------------------------|
| **Auth**         | None                                 | Email OTP via Redis + Brevo + JWT             |
| **State**        | In-memory dict + ChromaDB            | PostgreSQL (users/reports) + pgvector (vectors)|
| **Queue**        | Synchronous `asyncio.gather`         | Redis Streams (producer/consumer groups)     |
| **Worker**       | None (in-request LLM calls)         | Separate `worker.py` process                  |
| **LLM Keys**     | User-supplied per request            | Backend shared key (env var)                  |
| **Frontend UX**  | Recruiter dashboard, sync wait/timeout | Candidate portal, async "queued" state      |
| **Email**        | None                                 | Brevo (OTP + completion notification)         |
| **Storage**      | ChromaDB keyed by session_id        | PostgreSQL + pgvector keyed by resume_id      |
| **Session**      | In-memory dict                       | Redis-backed (survives restart, auto-expires) |
| **Chat**         | Resume-only RAG                      | Resume + JD + GitHub context with guardrails  |
| **Guardrails**   | None                                 | Modular package (7-layer security with two-tier injection/classification) |
| **Config**       | Scattered `os.environ`               | Centralized Pydantic BaseSettings             |
| **Migrations**   | `Base.metadata.create_all`           | Alembic + standalone SQL scripts              |

---

## Phase 1: Infrastructure & Dependencies -- DONE

- `requirements.txt`: pgvector, redis, asyncpg, sqlalchemy, pyjwt, prometheus, email-validator, pydantic-settings, alembic
- `.env.example`: All env vars configured
- `docker-compose.yml`: 3 services (backend, worker, frontend) with Alembic migration on startup

## Phase 2: Backend Storage & Session Overhaul -- DONE

- `services/database.py`: Engine + session factory + `CREATE EXTENSION vector`
- `services/storage/vector_store.py`: pgvector via SQLAlchemy, async methods requiring db session
- `services/storage/session_store.py`: Redis-backed async session store
- `services/redis.py`: Async Redis client (Upstash or local)
- `models/base.py`: SQLAlchemy DeclarativeBase
- `models/user.py`, `resume.py`, `chunk.py`, `report.py`: SQLAlchemy models (4 tables)
- `schemas/`: auth.py, upload.py, match.py, report.py, chat.py, common.py

## Phase 3: API Routing Changes -- DONE

- `api/auth.py`: OTP request + verify + JWT
- `api/upload.py`: Auth + file validation + document classification + security scans + SHA-256 dedup
- `api/match.py`: JD validation + Redis Stream producer + 202 + reports endpoints
- `api/chat.py`: Auth + query classification + RAG + JD/GitHub context + guardrails + streaming
- `main.py`: Auth router, DB/Redis lifecycle, Prometheus, health checks

## Phase 4: Background Worker -- DONE

- `worker.py`: Redis Stream consumer with retry/backoff, async matcher/vector_store
- `services/matching/matcher.py`: Async `compute_similarity` with chunk scoring, takes db session

## Phase 5: LLM Prompt Re-Engineering -- DONE

- `services/llm/client.py`: Config at init via env vars, document delimiters, hardened prompts
- `services/llm/prompts.py`: Domain-locked system prompts with "data only" rules

## Phase 6: Frontend UI/UX Flow -- DONE

- `AuthPage.jsx`: OTP digit boxes, step indicator, resend cooldown
- `UploadPage.jsx`: 3-step wizard with progress bar, drag-drop
- `Dashboard.jsx`: Report history sidebar, SVG ring gauge, collapsible sections, chat
- `App.jsx`: Auth guard, guest guard, `/auth`, `/dashboard/:reportId` routes
- `api.js`: JWT injection, all API functions
- `useBackendStatus.js`: 30s polling

## Phase 7: Configuration & Deployment -- DONE

- `Dockerfile`: Python 3.11, torch CPU, requirements.txt
- `Procfile`: web + worker + release (alembic) processes
- `render.yaml`: web + worker services
- `docker-compose.yml`: Runs `alembic upgrade head` before server start

## Phase 8: pgvector Migration -- DONE

- Removed `chromadb` from requirements
- Added `ResumeChunk` model with `Vector(384)` column
- Updated all callers for async vector_store interface with db session
- Removed `chroma_resume_id` from `master_resumes` table

## Phase 9: Chat Context Enhancement -- DONE

- Added `report_id` to `ChatRequest` schema
- Chat fetches `tailoring_reports` to get `jd_text` + `github_analysis`
- System prompt includes JD context, GitHub context, and resume RAG context

## Phase 10: Chat Guardrails -- DONE

- `services/guardrails.py`: Input validation + output sanitization
- Prompt injection detection (16 patterns)
- Off-topic keyword blocking (requires 2+ matches)
- Message length cap (2000 chars)
- Rate limiting (50 msgs/session/hour via Redis)
- Code block stripping + URL/link stripping from LLM output

## Phase 11: Codebase Restructuring -- DONE

- `config/settings.py`: Pydantic BaseSettings (single source for all env vars)
- `config/constants.py`: App-wide constants (JWT TTL, rate limits, upload limits)
- `core/security.py`: JWT encode/decode functions
- `core/dependencies.py`: Shared `get_current_user` dependency
- `models/base.py`: Single DeclarativeBase definition
- Services reorganized into subdirectories: `llm/`, `embedding/`, `matching/`, `parsing/`, `storage/`, `integrations/`
- Deleted 18 flat service files after reorganization

## Phase 12: Database Migrations -- DONE

- `migrations/001_initial_schema.sql`: Standalone SQL for Supabase SQL Editor
- `migrations/versions/001_initial_schema.py`: Alembic migration (tables + RLS)
- `alembic.ini`: Alembic configuration
- `Procfile`: Added `release: alembic upgrade head`

## Phase 13: Upload Security Hardening -- DONE

- `services/parsing/validator.py`: File type/size/page/text validation with magic-byte verification
- `services/parsing/classifier.py`: Document classification (resume/jd/other) via keyword heuristics
- Content moderation + document injection scanning
- `api/upload.py`: Full validation pipeline (4 layers before storage)
- `api/match.py`: JD validation (classification + injection + moderation)

## Phase 14: Chat Security Hardening -- DONE

- Query classification (recruitment keyword matching, 14 categories)
- Hardened system prompts with "data only" rules
- Document delimiters in LLM client

## Phase 15: Guardrails Refactor + Security Upgrade -- DONE

- Split monolithic `services/guardrails.py` into `services/guardrails/` package (6 modules)
- Two-tier document classification: keyword heuristics + LLM fallback with confidence
- Two-tier injection detection: regex patterns + LLM classifier
- `validate_message()` now async (supports LLM injection check)
- Combined `validate_upload()` and `validate_jd_text()` helpers
- Authorization checks on all resource endpoints (github, search, session)
- JD embedding caching in Redis (SHA-256 key, 24h TTL)
- Explainable scoring with category breakdown (skills, experience, education, projects, keywords)

## Phase 16: Brevo Email Integration -- DONE

- `services/integrations/brevo.py`: Brevo SMTP API via httpx
- OTP email: branded HTML template with 6-digit code
- Report completion email: ATS score + dashboard link
- `api/auth.py`: Full OTP flow (request-otp, verify-otp, anonymous)
- `worker.py`: Sends report completion email after job finishes
- `config/settings.py`: Brevo API key, sender email, sender name
- Replaced Resend with Brevo in `.env.example`

---

## Security Notes

1. LLM API key is server-side only (never sent to frontend)
2. JWT tokens stored in localStorage, validated on all protected endpoints
3. Rate limiting on OTP endpoints (3/email/5min)
4. Rate limiting on chat (50 msgs/session/hour)
5. SHA-256 resume deduplication prevents re-processing
6. **Upload security**: Magic-byte verification, size/page/text limits, two-tier document classification, content moderation, two-tier injection scanning
7. **JD validation**: Two-tier classification check, injection scan, content moderation, length limit
8. **Chat security**: Query classification, two-tier injection detection, rate limiting, output sanitization
9. **Prompt hardening**: "Data only" instructions, document delimiters, domain lock, no prompt disclosure
10. **Authorization**: All resource endpoints verify user_id ownership (returns 404)
11. Alembic migrations for schema versioning
12. Centralized config (no hardcoded secrets)

---

## Production-Grade Features Checklist

- [x] Redis-backed session store (survives restarts, auto-expires)
- [x] PostgreSQL + pgvector for persistent data AND embeddings
- [x] Redis Streams for async job processing
- [x] Email OTP via Brevo (branded HTML templates)
- [x] Report completion emails via Brevo (score + dashboard link)
- [x] JWT authentication with rate limiting
- [x] OTP-based email verification (Redis-backed, 5min TTL)
- [x] SHA-256 resume deduplication
- [x] JD embedding caching (Redis, SHA-256 key, 24h TTL)
- [x] Prometheus metrics (request latency, error rates, throughput)
- [x] Health check endpoint (DB + Redis)
- [x] Graceful shutdown (DB pool, Redis connections)
- [x] Retry with exponential backoff in worker
- [x] Dead letter stream for failed jobs
- [x] Rate limiting on OTP (3/5min) and chat (50 msgs/session/hour)
- [x] Upload validation (magic bytes, size, pages, text length)
- [x] Two-tier document classification (heuristic + LLM)
- [x] Two-tier injection detection (regex + LLM)
- [x] Content moderation (unsafe content detection)
- [x] Query classification (recruitment-domain enforcement)
- [x] JD validation (classification + injection + moderation)
- [x] Chat guardrails (injection, off-topic, output sanitization)
- [x] Hardened LLM prompts with document delimiters
- [x] Authorization checks on all resource endpoints
- [x] Modular guardrails package (6 focused modules)
- [x] Explainable scoring with category breakdowns
- [x] Centralized config (Pydantic BaseSettings)
- [x] Shared auth dependency (no duplication)
- [x] Alembic database migrations
- [x] Service directory organization

---

## Files Summary

### New Files (Phases 15-16)
- `backend/services/guardrails/__init__.py` -- Re-exports all guardrail functions
- `backend/services/guardrails/injection.py` -- Regex + LLM injection detection
- `backend/services/guardrails/moderation.py` -- Content moderation patterns
- `backend/services/guardrails/query.py` -- Query classification + recruitment validation
- `backend/services/guardrails/output.py` -- Output sanitization
- `backend/services/guardrails/rate_limit.py` -- Redis-based rate limiting
- `backend/services/guardrails/upload.py` -- Upload/JD validation helpers
- `backend/services/integrations/brevo.py` -- Brevo email service (OTP + report notifications)

### Modified Files (Phases 15-16)
- `backend/api/auth.py` -- Full OTP flow (request-otp, verify-otp, anonymous) with Brevo
- `backend/api/upload.py` -- Uses modular guardrails, two-tier classification
- `backend/api/match.py` -- Uses validate_jd_text, two-tier classification
- `backend/api/chat.py` -- Async validate_message, modular guardrails imports
- `backend/api/github.py` -- Added auth + ownership check
- `backend/api/search.py` -- Added auth + ownership check
- `backend/api/session.py` -- Added auth + ownership check
- `backend/services/llm/client.py` -- Added classify_document, detect_injection methods
- `backend/services/llm/prompts.py` -- Added CLASSIFICATION_SYSTEM_PROMPT
- `backend/services/matching/matcher.py` -- JD caching, category breakdown
- `backend/config/settings.py` -- Brevo config fields
- `backend/config/constants.py` -- JD_EMBEDDING_CACHE_TTL
- `backend/worker.py` -- Passes redis to matcher, sends Brevo email on completion
- `backend/schemas/auth.py` -- RequestOTPRequest, VerifyOTPRequest, EmailStr
- `backend/requirements.txt` -- Added email-validator
- `backend/.env.example` -- Brevo config (replaced Resend)
- `ARCHITECTURE.md`, `README.md`, `MIGRATION_PLAN.md` -- Updated documentation

### Deleted Files (Phase 15)
- `backend/services/guardrails.py` (replaced by guardrails/ package)
