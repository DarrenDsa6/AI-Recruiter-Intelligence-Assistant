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

## Phase 17: Storage Optimization & TTL Cleanup -- DONE

- `services/cleanup/purger.py`: TTL-based deletion of old chunks (7d), reports (14d), orphaned resumes
- `services/storage/vector_store.py`: Text stored directly in text column for all chunks (resume + github); simplified reads with no offset reconstruction
- `services/matching/matcher.py`: Derives skills at query time via SkillExtractionService when not stored
- `services/parsing/chunker.py`: Returns `list[dict]` with `text`, `start`, `end` offsets
- `worker.py`: Periodic cleanup every 100 stream polls (~17min)
- `config/constants.py`: CHUNK_RETENTION_DAYS=7, REPORT_RETENTION_DAYS=14

## Phase 18: Architecture Gap Fixes -- DONE

Fixed all discrepancies between ARCHITECTURE.md documentation and actual codebase:

- **SSE via Redis Pub/Sub**: Worker publishes `{"status": "completed/failed"}` to `report:{report_id}` channel after DB commit. SSE endpoint subscribes to Redis Pub/Sub instead of polling DB every 2s.
- **No localStorage**: Removed all `localStorage.setItem`/`getItem` calls from AuthPage, UploadPage, Dashboard. User email fetched from `GET /api/auth/me` via HttpOnly cookie.
- **pyproject.toml**: Removed chromadb dependency.
- **settings.py**: Removed Resend config fields (replaced by Brevo).

## Phase 19: Worker Reliability & Stream Management -- DONE

Fixed infinite retry loops and stale message accumulation:

- **ORM simplification**: Removed `chunk_start_char`/`chunk_end_char` columns from `ResumeChunk` model. All text stored directly in `text` column. Eliminated offset reconstruction logic.
- **Worker error handling**: On failure, rolls back aborted transaction, then uses a fresh DB session to mark report as "failed". Prevents infinite retry loops caused by failed UPDATE in aborted transaction.
- **Stream position persistence**: Worker stores `LAST_ID` in Redis key `worker:last_stream_id`. Survives container restarts — no re-reading old messages.
- **Stale stream flush**: On first boot (no saved position), worker flushes entire stream and starts from latest entry ("$").
- **Database pool_pre_ping**: Added `pool_pre_ping=True` to async engine to detect and recycle stale connections.
- **Worker healthcheck**: Docker Compose worker depends on backend `service_healthy` condition. Backend healthcheck uses Python urllib.
- **Alembic env.py fix**: Removed `connection.commit()` that broke alembic's transaction management, preventing migration version from being updated.
- **Migration 002**: Simplified to no-op (columns removed from model).

## Phase 20: Security Hardening & Bug Fixes -- DONE

- **Timing-safe OTP comparison**: `hmac.compare_digest()` prevents timing attacks on OTP verification
- **JWT secret validation**: App exits at startup if JWT_SECRET is empty (prevents unsigned tokens)
- **Anonymous login rate limiting**: Global limit of 5 anonymous sessions per hour
- **GitHub token security**: Moved from URL query param to X-GitHub-Token header (prevents log leakage)
- **GitHub username validation**: Regex validation prevents path traversal on GitHub API
- **Pickle removal**: Replaced `pickle.load()` with `np.load(allow_pickle=True)` in skill cache (prevents arbitrary code execution)
- **Exception sanitization**: All API endpoints return generic error messages (no internal details leaked)
- **Atomic Redis rate limiting**: All rate limiters use pipeline (incr+expire in one round trip, no race condition)
- **Session store race condition**: add_message uses pipeline for atomic read-modify-write
- **Worker consumer uniqueness**: Consumer name uses hostname-pid (prevents collision between instances)
- **Worker priority starvation fix**: Both urgent and email streams checked each loop iteration
- **SSE polling timeout**: 5-minute timeout prevents infinite polling (150 polls × 2s)
- **SSE poll authorization**: Poll query includes user_id (prevents unauthorized status tracking)
- **Worker error handling**: Missing report_id handled gracefully; generic error messages in DB
- **Worker xclaim safety**: min_idle_time=60000 prevents claiming actively-processed messages
- **PyMuPDF double-close fix**: Removed redundant doc.close() in validator (prevents segfault)
- **Vector store commit**: delete_by_resume calls flush() (prevents silent data loss)
- **LLM empty choices**: Handled gracefully (no IndexError crash)
- **Frontend env vars**: All import.meta.env.VITE_API_URL → process.env.REACT_APP_API_URL (was broken in Docker)
- **Dashboard markdown**: AI chat messages rendered with ReactMarkdown
- **Dashboard state mutation**: Immutable updates (prevents React re-render bugs)
- **Dashboard unmount cleanup**: SSE stream uses AbortController
- **Chat error feedback**: Stream errors shown in chat UI
- **N+1 query fix**: /reports endpoint uses bulk fetch instead of per-report query
- **Schema validation**: max_length on ChatRequest.message (2000) and MatchRequest.jd_text (50000)
- **CORS hardening**: Restricted to specific methods and headers
- **Cookie security**: Delete cookie has httponly/secure/samesite flags
- **Content-Security-Policy**: Added to index.html
- **Nginx SSE headers**: Connection '', proxy_http_version 1.1, chunked_transfer_encoding off
- **Email normalization**: Auth emails normalized (lowercase, strip)
- **Off-topic guardrail**: Threshold lowered from 2 to 1 match; short messages no longer bypass
- **postgres:// URL conversion**: settings.py handles Heroku-style postgres:// URLs
- **Embedder returns lists**: get_embeddings() returns Python lists, not numpy arrays
- **Report API resume_id**: /reports and /reports/:id responses include resume_id

## Phase 21: Deep Scan Bug Fixes -- DONE

Fixed 15 bugs identified by comprehensive codebase audit:

- **Worker retry counter**: `parse_payload()` reads retries from `payload.get("retries", 0)` instead of outer `data` variable (was always 0, causing infinite retries)
- **Worker XCLAIM recovery**: Uses XPENDING → fetch actual msg IDs → XCLAIM (was hardcoded `["0-0"]` which never matched real messages)
- **Worker stale continue**: Removed `continue` after email entries that caused tight CPU loop
- **Session delete commit**: Added `await db.commit()` after `delete_by_resume` in `delete_session`; fixed `end_router` → `router` typo
- **Upload atomicity**: Two-commit pattern replaced with `db.flush()` + single commit (prevents orphaned resumes)
- **Async embedding**: Sync `embed_documents()`/`get_embeddings()` wrapped in `asyncio.to_thread()` in chat.py, search.py, upload.py, matcher.py (was blocking event loop)
- **LLM stream errors**: `stream_chat()` now re-raises exceptions instead of silently returning empty response
- **O(n²) sanitize**: Chat SSE sanitization moved to final output only (was re-sanitizing entire cumulative string per token)
- **Vector store distances**: `query_by_resume` returns actual cosine distances (was hardcoded `0.0`)
- **Chunker infinite loop**: Guard against `overlap >= chunk_size` with ValueError
- **Auth race condition**: IntegrityError on concurrent duplicate email handled with rollback + re-fetch
- **Embedder normalization**: `embed_documents()` now uses `normalize_embeddings=True` (was inconsistent with `get_embeddings()`)
- **UploadPage stale closure**: `githubUsername` added to `useCallback` deps (GitHub ingest never ran)
- **AbortController cleanup**: Dashboard + ChatSection store AbortController in ref and abort on unmount
- **AuthPage unhandled rejection**: `.catch()` added to OTP resend promise
- **ChatSection duplicate error**: Removed redundant `setCurrentAI` + `setMessages` on error (showed two error messages)

---

## Security Notes

1. LLM API key is server-side only (never sent to frontend)
2. JWT tokens stored in HttpOnly cookie, validated on all protected endpoints
3. Rate limiting on OTP endpoints (3/email/5min)
4. Rate limiting on chat (50 msgs/session/hour)
5. Rate limiting on matches (5/day/user)
6. SHA-256 resume deduplication prevents re-processing
7. **Upload security**: Magic-byte verification, size/page/text limits, two-tier document classification, content moderation, two-tier injection scanning
8. **JD validation**: Two-tier classification check, injection scan, content moderation, length limit
9. **Chat security**: Query classification, two-tier injection detection, rate limiting, output sanitization
10. **Prompt hardening**: "Data only" instructions, document delimiters, domain lock, no prompt disclosure
11. **Authorization**: All resource endpoints verify user_id ownership (returns 404)
12. **PII scrubbing**: Resume text scrubbed before LLM calls (emails, phones, SSNs, credit cards, IPs, addresses)
13. **TTL auto-cleanup**: Old chunks (7d), reports (14d), and orphaned resumes purged automatically
14. **Timing-safe OTP**: hmac.compare_digest prevents timing attacks
15. **JWT secret validation**: App fails fast if JWT_SECRET is empty
16. **Anonymous login rate limit**: 5/hour global cap
17. **GitHub security**: Token in header (not URL), username regex validation
18. **No pickle**: np.load with allow_pickle=True instead of pickle.load
19. **Exception sanitization**: Generic error messages only
20. **Atomic rate limiting**: Redis pipeline (no race conditions)
21. **Worker safety**: hostname-pid consumer, xclaim min_idle, priority starvation fix
22. **SSE hardening**: 5-min timeout, user_id authorization
23. **PyMuPDF fix**: No double-close (prevents segfault)
24. **CORS hardening**: Restricted methods and headers
25. **Cookie security**: httponly/secure/samesite on delete
26. **Content-Security-Policy**: Added to index.html
27. **Email normalization**: Lowercase + strip on auth
28. **Off-topic guardrail**: Threshold lowered, short messages no longer bypass
29. Alembic migrations for schema versioning
30. Centralized config (no hardcoded secrets)

---

## Production-Grade Features Checklist

- [x] Redis-backed session store (survives restarts, auto-expires)
- [x] PostgreSQL + pgvector for persistent data AND embeddings
- [x] Redis Streams for async job processing
- [x] Stream trimming (XTRIM MAXLEN ~50) to prevent unbounded accumulation
- [x] Idempotency check to skip already-processed reports on worker restart
- [x] Email OTP via Brevo (branded HTML templates)
- [x] Report completion emails via Brevo (score + dashboard link + PDF attachment)
- [x] JWT authentication with HttpOnly cookie
- [x] OTP-based email verification (Redis-backed, 5min TTL)
- [x] SHA-256 resume deduplication
- [x] JD embedding caching (Redis, SHA-256 key, 24h TTL)
- [x] TTL auto-cleanup (7d chunks, 14d reports, orphaned resumes)
- [x] Text stored directly in text column (simplified reads)
- [x] Skill derivation at query time (5% storage savings)
- [x] PII scrubbing before LLM calls
- [x] Daily match rate limiting (5/day/user)
- [x] SSE streaming for job status updates
- [x] Layout-aware PDF parsing
- [x] Prometheus metrics (request latency, error rates, throughput)
- [x] Health check endpoint (DB + Redis, cached 30s)
- [x] Worker depends on backend healthcheck (docker-compose)
- [x] Graceful shutdown (DB pool, Redis connections)
- [x] Worker error handling with fresh session on failure
- [x] Stream position persisted in Redis (survives restarts)
- [x] Stale stream flush on first boot
- [x] pool_pre_ping on database engine
- [x] Rate limiting on OTP (3/5min), chat (50 msgs/session/hour), and matches (5/day)
- [x] Upload validation (magic bytes, size, pages, text length)
- [x] Two-tier document classification (heuristic + LLM)
- [x] Two-tier injection detection (regex + LLM)
- [x] Content moderation (unsafe content detection)
- [x] Query classification (recruitment-domain enforcement)
- [x] JD validation (classification + injection + moderation)
- [x] Chat guardrails (injection, off-topic, output sanitization)
- [x] Hardened LLM prompts with document delimiters
- [x] Authorization checks on all resource endpoints
- [x] Modular guardrails package (7 focused modules including PII)
- [x] Explainable scoring with category breakdowns
- [x] Centralized config (Pydantic BaseSettings)
- [x] Shared auth dependency (no duplication)
- [x] Alembic database migrations
- [x] Service directory organization
- [x] Timing-safe OTP comparison (hmac.compare_digest)
- [x] JWT secret validation at startup
- [x] Anonymous login rate limiting (5/hour)
- [x] GitHub token in header (not URL)
- [x] GitHub username regex validation
- [x] Pickle replaced with np.load(allow_pickle=True)
- [x] Exception sanitization on all API endpoints
- [x] Atomic Redis rate limiting (pipeline)
- [x] Atomic session message add (pipeline)
- [x] Worker hostname-pid consumer name
- [x] Worker priority starvation fix
- [x] SSE polling timeout (5 min)
- [x] SSE poll authorization (user_id)
- [x] Worker xclaim min_idle_time safety
- [x] PyMuPDF double-close fix
- [x] Vector store flush on delete
- [x] LLM empty choices handling
- [x] Frontend env vars for Docker (REACT_APP_API_URL)
- [x] ReactMarkdown in dashboard chat
- [x] Immutable state updates in Dashboard
- [x] SSE AbortController cleanup on unmount
- [x] Chat error feedback in UI
- [x] N+1 query fix on /reports endpoint
- [x] Schema max_length validation (chat + match)
- [x] CORS hardened (specific methods/headers)
- [x] Cookie security flags on delete
- [x] Content-Security-Policy header
- [x] Nginx SSE proxy headers
- [x] Email normalization (lowercase, strip)
- [x] Off-topic guardrail threshold lowered
- [x] postgres:// URL conversion
- [x] Embedder returns Python lists
- [x] Report API includes resume_id
- [x] Worker retry counter from payload (not outer variable)
- [x] Worker XPENDING + XCLAIM recovery (not hardcoded "0-0")
- [x] Async embedding calls via asyncio.to_thread()
- [x] LLM stream_chat re-raises errors
- [x] Chat sanitize on final output only (not O(n²) cumulative)
- [x] Vector store returns actual cosine distances
- [x] Chunker validates overlap < chunk_size
- [x] Auth IntegrityError race condition handled
- [x] Embedder embed_documents uses normalize_embeddings
- [x] UploadPage stale closure fixed (githubUsername in deps)
- [x] AbortController cleanup on Dashboard + ChatSection unmount
- [x] AuthPage OTP resend unhandled rejection fixed
- [x] ChatSection duplicate error message removed

---

## Files Summary

### New Files (Phases 15-18)
- `backend/services/guardrails/__init__.py` -- Re-exports all guardrail functions
- `backend/services/guardrails/injection.py` -- Regex + LLM injection detection
- `backend/services/guardrails/moderation.py` -- Content moderation patterns
- `backend/services/guardrails/query.py` -- Query classification + recruitment validation
- `backend/services/guardrails/output.py` -- Output sanitization
- `backend/services/guardrails/rate_limit.py` -- Redis-based rate limiting
- `backend/services/guardrails/upload.py` -- Upload/JD validation helpers
- `backend/services/guardrails/pii.py` -- PII scrubbing (emails, phones, SSNs, credit cards, IPs, addresses)
- `backend/services/integrations/brevo.py` -- Brevo email service (OTP + report notifications)
- `backend/services/cleanup/__init__.py` -- Cleanup module exports
- `backend/services/cleanup/purger.py` -- TTL-based data purger (chunks, reports, orphaned resumes)
- `backend/services/pdf/__init__.py` -- PDF report generation (fpdf2)
- `backend/migrations/versions/002_add_chunk_offsets.py` -- Alembic migration for chunk offset columns

### Modified Files (Phases 15-21)
- `backend/api/auth.py` -- Full OTP flow (request-otp, verify-otp, anonymous) with Brevo + HttpOnly cookie
- `backend/api/upload.py` -- Uses modular guardrails, two-tier classification, no offset metadata
- `backend/api/match.py` -- Uses validate_jd_text, two-tier classification, daily rate limit, email opt-in, SSE via Redis Pub/Sub
- `backend/api/chat.py` -- Async validate_message, modular guardrails imports, optional resume_id
- `backend/api/github.py` -- Added auth + ownership check, no offset metadata
- `backend/api/search.py` -- Added auth + ownership check
- `backend/api/session.py` -- Added auth + ownership check
- `backend/models/chunk.py` -- Simplified: removed chunk_start_char/chunk_end_char columns
- `backend/services/llm/client.py` -- Added classify_document, detect_injection methods, timeout/retry
- `backend/services/llm/prompts.py` -- Added CLASSIFICATION_SYSTEM_PROMPT
- `backend/services/matching/matcher.py` -- JD caching, category breakdown, skill derivation at query time
- `backend/services/parsing/chunker.py` -- Returns list[dict] with text, start, end offsets
- `backend/services/storage/vector_store.py` -- Text stored directly; no offset reconstruction; simplified reads
- `backend/services/database.py` -- Added pool_pre_ping=True
- `backend/migrations/env.py` -- Removed connection.commit() that broke transaction management
- `backend/migrations/versions/002_add_chunk_offsets.py` -- Simplified to no-op (columns removed from model)
- `backend/worker.py` -- Stream position in Redis, flush on first boot, fresh session on error, XREAD
- `backend/config/settings.py` -- Brevo config fields, removed Resend
- `backend/config/constants.py` -- JD_EMBEDDING_CACHE_TTL, CHUNK_RETENTION_DAYS, REPORT_RETENTION_DAYS
- `backend/schemas/auth.py` -- RequestOTPRequest, VerifyOTPRequest, EmailStr
- `backend/schemas/match.py` -- send_email field
- `backend/schemas/chat.py` -- Optional resume_id
- `backend/requirements.txt` -- Added email-validator, fpdf2
- `backend/pyproject.toml` -- Removed chromadb
- `backend/.env.example` -- Brevo config (replaced Resend)
- `docker-compose.yml` -- Worker depends on backend healthcheck
- `frontend/recruiter-ui/src/pages/AuthPage.jsx` -- Removed localStorage calls
- `frontend/recruiter-ui/src/pages/UploadPage.jsx` -- User email from /api/auth/me, sign-out
- `frontend/recruiter-ui/src/pages/Dashboard.jsx` -- User email from /api/auth/me, sign-out
- `frontend/recruiter-ui/src/components/ChatSection.jsx` -- import.meta.env.VITE_API_URL, credentials:include
- `frontend/recruiter-ui/src/services/api.js` -- credentials:include on all requests
- `ARCHITECTURE.md`, `README.md`, `MIGRATION_PLAN.md`, `PROJECT_FLOW.md` -- Updated documentation

### Modified Files (Phase 21: Deep Scan Fixes)
- `backend/worker.py` -- Retry counter from payload, XPENDING+XCLAIM recovery, stale continue removed
- `backend/api/session.py` -- Missing commit after delete, end_router typo fixed
- `backend/api/upload.py` -- Two-commit replaced with flush+single commit, asyncio.to_thread for embeddings
- `backend/api/chat.py` -- asyncio.to_thread for embeddings, O(n²) sanitize fixed
- `backend/api/search.py` -- asyncio.to_thread for embeddings
- `backend/services/matching/matcher.py` -- asyncio.to_thread for embeddings, _score_chunks made async
- `backend/services/llm/client.py` -- stream_chat re-raises errors instead of silent return
- `backend/services/storage/vector_store.py` -- Returns actual cosine distances
- `backend/services/parsing/chunker.py` -- Validates overlap < chunk_size
- `backend/services/embedding/embedder.py` -- normalize_embeddings=True on embed_documents
- `backend/api/auth.py` -- IntegrityError handled on duplicate email
- `frontend/recruiter-ui/src/pages/UploadPage.jsx` -- githubUsername in useCallback deps
- `frontend/recruiter-ui/src/pages/Dashboard.jsx` -- AbortController ref + unmount cleanup
- `frontend/recruiter-ui/src/pages/AuthPage.jsx` -- .catch() on OTP resend
- `frontend/recruiter-ui/src/components/ChatSection.jsx` -- AbortController + duplicate error removed

### Deleted Files (Phase 15)
- `backend/services/guardrails.py` (replaced by guardrails/ package)
