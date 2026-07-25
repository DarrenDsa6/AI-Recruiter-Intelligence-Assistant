# Migration Plan: Synchronous Recruiter -> Async Candidate Platform

## Summary

Pivot the AI Recruiter Intelligence Assistant from a synchronous, recruiter-facing tool
to an asynchronous, candidate-facing platform with persistent storage, email-based auth,
Redis Streams-backed job queue, pgvector embeddings, multi-layer security, and a re-engineered UX flow.

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
| **Guardrails**   | None                                 | 7-layer security (validation, classification, moderation, injection, query classification, prompt hardening, output sanitization) |
| **Config**       | Scattered `os.environ`               | Centralized Pydantic BaseSettings             |
| **Migrations**   | `Base.metadata.create_all`           | Alembic + standalone SQL scripts              |

---

## Phase 1: Infrastructure & Dependencies -- DONE

- `requirements.txt`: pgvector, redis, asyncpg, sqlalchemy, resend, pyjwt, prometheus, email-validator, pydantic-settings, alembic
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

## Phase 11: Codebase Restructuring -- DONE

- `config/settings.py`: Pydantic BaseSettings (single source for all env vars)
- `config/constants.py`: App-wide constants (JWT TTL, rate limits, upload limits)
- `core/security.py`: JWT encode/decode functions
- `core/dependencies.py`: Shared `get_current_user` dependency (eliminates 3x duplication)
- `models/base.py`: Single DeclarativeBase definition
- Services reorganized into subdirectories: `llm/`, `embedding/`, `matching/`, `parsing/`, `storage/`, `integrations/`
- Deleted 18 flat service files after reorganization
- Updated all internal imports across 30+ files

## Phase 12: Database Migrations -- DONE

- `migrations/001_initial_schema.sql`: Standalone SQL for Supabase SQL Editor (no transaction wrapper)
- `migrations/versions/001_initial_schema.py`: Alembic migration (tables + RLS policies)
- `migrations/env.py`: Alembic environment config
- `alembic.ini`: Alembic configuration
- `Procfile`: Added `release: alembic upgrade head`
- `docker-compose.yml`: Updated to run migrations before server start

## Phase 13: Upload Security Hardening -- DONE

- `services/parsing/validator.py`: File type/size/page/text validation with magic-byte verification
- `services/parsing/classifier.py`: Document classification (resume/jd/other) via keyword heuristics
- `services/guardrails.py`: Content moderation + document injection scanning
- `api/upload.py`: Full validation pipeline (4 layers before storage)
- `api/match.py`: JD validation (classification + injection + moderation)
- `config/constants.py`: Upload limits (10MB, 30 pages, 50K chars) + recruitment keywords

## Phase 14: Chat Security Hardening -- DONE

- `services/guardrails.py`: Query classification (recruitment keyword matching, 14 categories)
- `services/llm/prompts.py`: Hardened system prompts with "data only" rules
- `services/llm/client.py`: Document delimiters (`<<<DOCUMENT_DATA_START>>>`/`<<<DOCUMENT_DATA_END>>>`)
- `api/chat.py`: Uses `CHAT_SYSTEM_PROMPT_TEMPLATE` + delimited context

---

## Security Notes

1. LLM API key is server-side only (never sent to frontend)
2. JWT tokens stored in localStorage, validated on all protected endpoints
3. Rate limiting on OTP endpoints (3/email/5min, 10/IP/hr)
4. Rate limiting on chat (50 msgs/session/hour)
5. SHA-256 resume deduplication prevents re-processing
6. **Upload security**: Magic-byte verification, size/page/text limits, document classification, content moderation, injection scanning
7. **JD validation**: Classification check, injection scan, content moderation, length limit
8. **Chat security**: Query classification, injection detection, rate limiting, output sanitization
9. **Prompt hardening**: "Data only" instructions, document delimiters, domain lock, no prompt disclosure
10. Alembic migrations for schema versioning
11. Centralized config (no hardcoded secrets)

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
- [x] Upload validation (magic bytes, size, pages, text length)
- [x] Document classification (resume/jd/other)
- [x] Content moderation (unsafe content detection)
- [x] Prompt injection defense (document scanning + hardened prompts + delimiters)
- [x] Query classification (recruitment-domain enforcement)
- [x] JD validation (classification + injection + moderation)
- [x] Centralized config (Pydantic BaseSettings)
- [x] Shared auth dependency (no duplication)
- [x] Alembic database migrations
- [x] Service directory organization (llm/, embedding/, matching/, parsing/, storage/, integrations/)

---

## Files Summary

### New Files (Phases 11-14)
- `backend/config/settings.py` -- Pydantic BaseSettings (centralized env config)
- `backend/config/constants.py` -- App-wide constants (upload limits, recruitment keywords)
- `backend/core/security.py` -- JWT encode/decode
- `backend/core/dependencies.py` -- Shared get_current_user
- `backend/models/base.py` -- SQLAlchemy DeclarativeBase
- `backend/services/redis.py` -- Renamed from redis_client.py
- `backend/services/llm/client.py` -- LLM client with document delimiters
- `backend/services/llm/prompts.py` -- Hardened system prompts
- `backend/services/embedding/embedder.py` -- Renamed from embedding_service.py
- `backend/services/embedding/model_registry.py` -- Renamed from model_registry.py
- `backend/services/embedding/skill_cache.py` -- Extracted from flat structure
- `backend/services/matching/matcher.py` -- Main orchestrator
- `backend/services/matching/semantic_matcher.py` -- Extracted
- `backend/services/matching/skill_classifier.py` -- Extracted
- `backend/services/matching/skill_gap_analyzer.py` -- Extracted
- `backend/services/matching/explainer.py` -- Extracted
- `backend/services/parsing/parser.py` -- Renamed from parser.py
- `backend/services/parsing/chunker.py` -- Renamed from chunker.py
- `backend/services/parsing/skills.py` -- Renamed from skills.py
- `backend/services/parsing/validator.py` -- NEW: File/text validation
- `backend/services/parsing/classifier.py` -- NEW: Document classification
- `backend/services/storage/vector_store.py` -- Renamed from vector_store.py
- `backend/services/storage/session_store.py` -- Renamed from session_store.py
- `backend/services/integrations/github.py` -- Renamed from github_service.py
- `backend/services/guardrails.py` -- Enhanced with moderation + query classification
- `backend/migrations/001_initial_schema.sql` -- Standalone SQL
- `backend/migrations/env.py` -- Alembic env
- `backend/migrations/script.py.mako` -- Alembic template
- `backend/migrations/versions/001_initial_schema.py` -- Alembic migration
- `backend/alembic.ini` -- Alembic config
- `backend/.env.example` -- Backend env template
- `frontend/recruiter-ui/.env.example` -- Frontend env template

### Modified Files (Phases 11-14)
- `backend/main.py` -- Uses config.settings, new imports
- `backend/worker.py` -- Uses config.constants, new imports
- `backend/build_skill_cache.py` -- Uses config.settings
- `backend/api/auth.py` -- Uses get_current_user, new service imports
- `backend/api/upload.py` -- Full validation pipeline (4 layers)
- `backend/api/match.py` -- JD validation (classification + injection + moderation)
- `backend/api/chat.py` -- Query classification + hardened prompts + delimiters
- `backend/api/github.py` -- New service imports
- `backend/api/search.py` -- New service imports
- `backend/api/session.py` -- New service imports
- `backend/api/__init__.py` -- Includes search_router
- `backend/models/__init__.py` -- Imports all models
- `backend/models/user.py` -- Imports from base.py
- `backend/models/resume.py` -- Imports from base.py
- `backend/models/chunk.py` -- Imports from base.py
- `backend/models/report.py` -- Imports from base.py
- `backend/schemas/upload.py` -- Added UploadRejectResponse
- `backend/schemas/__init__.py` -- Updated imports
- `backend/services/__init__.py` -- Updated imports
- `backend/requirements.txt` -- Added pydantic-settings, alembic
- `backend/Procfile` -- Added release: alembic upgrade head
- `docker-compose.yml` -- Runs alembic upgrade head before server
- `.gitignore` -- Updated
- `frontend/recruiter-ui/.gitignore` -- Added .env
- `frontend/recruiter-ui/.env` -- Cleaned (only VITE_API_URL)

### Deleted Files (Phase 11)
- `backend/services/chunker.py` (moved to parsing/)
- `backend/services/db.py` (moved to services/database.py)
- `backend/services/embedding_service.py` (moved to embedding/)
- `backend/services/explainer.py` (moved to matching/)
- `backend/services/github_service.py` (moved to integrations/)
- `backend/services/jd_skill_classifier.py` (moved to matching/)
- `backend/services/llm_service.py` (moved to llm/)
- `backend/services/matcher.py` (moved to matching/)
- `backend/services/model_registry.py` (moved to embedding/)
- `backend/services/parser.py` (moved to parsing/)
- `backend/services/provider_config.py` (removed)
- `backend/services/redis_client.py` (renamed to redis.py)
- `backend/services/semantic_matcher.py` (moved to matching/)
- `backend/services/session_store.py` (moved to storage/)
- `backend/services/skill_embedding_cache.py` (moved to embedding/)
- `backend/services/skills.py` (moved to parsing/)
- `backend/services/vector_store.py` (moved to storage/)
- `backend/services/weighted_skill_gap_analyzer.py` (moved to matching/)
- `E:\AIRecruiter\database.py` (stale root-level duplicate)
