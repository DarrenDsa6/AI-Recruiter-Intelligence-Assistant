# Migration Plan: Synchronous Recruiter -> Async Candidate Platform

## Summary

Pivot the AI Recruiter Intelligence Assistant from a synchronous, recruiter-facing tool
to an asynchronous, candidate-facing platform with persistent storage, email-based auth,
Redis Streams-backed job queue, and a re-engineered UX flow.

---

## Architecture Comparison

| Layer            | Current                              | Target                                        |
|------------------|--------------------------------------|-----------------------------------------------|
| **Auth**         | None                                 | Email OTP via Redis + JWT                     |
| **State**        | In-memory dict + ChromaDB            | PostgreSQL (users/reports) + ChromaDB (vectors)|
| **Queue**        | Synchronous `asyncio.gather`         | Redis Streams (producer/consumer groups)     |
| **Worker**       | None (in-request LLM calls)         | Separate `worker.py` process                  |
| **LLM Keys**     | User-supplied per request            | Backend shared key (env var)                  |
| **Frontend UX**  | Recruiter dashboard, sync wait/timeout | Candidate portal, async "queued" state      |
| **Email**        | None                                 | Resend (magic link after processing)          |
| **Storage**      | ChromaDB keyed by session_id        | ChromaDB keyed by resume_id (persistent)      |
| **Session**      | In-memory dict                       | Redis-backed (survives restart, auto-expires) |

---

## Phase 1: Infrastructure & Dependencies

### 1.1 New Environment Variables

Add to `.env.example` and `docker-compose.yml`:

```
SUPABASE_URL=...
SUPABASE_KEY=...
REDIS_URL=...              # Upstash Redis REST URL (OTP + sessions + job queue)
RESEND_API_KEY=...         # Resend email API key
RESEND_FROM_EMAIL=...      # Verified sender email
LLM_API_KEY=...            # Single shared key for backend LLM calls
JWT_SECRET=...             # Secret for signing JWT tokens
```

### 1.2 New Python Packages

Add to `backend/requirements.txt`:

```
redis[hiredis]            # Redis client for OTP, sessions, rate limits, job queue
asyncpg                   # Async PostgreSQL driver
sqlalchemy[asyncio]       # ORM + query builder
resend                    # Email sending
pyjwt                     # JWT token creation/verification
prometheus-fastapi-instrumentator  # Request metrics
```

### 1.3 Service Accounts to Create

| Service    | Provider     | Free Tier        | Purpose                     |
|------------|--------------|------------------|-----------------------------|
| Redis      | Upstash      | 10K cmds/day     | OTP, sessions, rate limits, job queue |
| PostgreSQL | Supabase/Neon| 500MB            | Users, reports, metadata    |
| Email      | Resend       | 3K emails/mo     | OTP codes, magic links      |

---

## Phase 2: Backend Storage & Session Overhaul

### 2.1 New File: `backend/services/db.py`

PostgreSQL connection pool using `asyncpg` + `SQLAlchemy[asyncio]`.

**Tables:**

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_login TIMESTAMPTZ
);

CREATE TABLE master_resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    file_hash TEXT NOT NULL,              -- SHA-256 of uploaded file
    raw_text TEXT NOT NULL,
    chroma_resume_id TEXT NOT NULL,       -- key used in ChromaDB
    filename TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, file_hash)
);

CREATE TABLE tailoring_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    resume_id UUID REFERENCES master_resumes(id) ON DELETE CASCADE,
    jd_text TEXT NOT NULL,
    status TEXT DEFAULT 'pending',        -- pending | processing | completed | failed
    match_result JSONB,
    github_analysis JSONB,
    report JSONB,
    questions JSONB,
    rewrites JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);
```

**Impact:** All files that currently use `session_store` or pass `session_id` to
`vector_store` must be updated.

### 2.2 Modify: `backend/services/vector_store.py`

- Rename parameter `session_id` -> `resume_id` in all methods
  - `add_documents(documents, embeddings, metadatas, resume_id)`
  - `get_by_session(resume_id)` -> rename to `get_by_resume(resume_id)`
  - `delete_by_session(resume_id)` -> rename to `delete_by_resume(resume_id)`
  - `query_by_session(resume_id, ...)` -> rename to `query_by_resume(resume_id, ...)`
- Change collection name from `ai_recruiter_collection` to `candidate_resumes`
- Embeddings now persist across job applications for the same resume

**Files affected by this change:**
- `backend/api/upload.py` -- `vector_store.add_documents(session_id=X)` -> `resume_id=X`
- `backend/api/match.py` -- `vector_store.get_by_session(X)` -> `get_by_resume(X)`
- `backend/api/chat.py` -- all vector_store calls
- `backend/api/github.py` -- `vector_store.add_documents(session_id=X)`
- `backend/api/search.py` -- `vector_store.get_by_session(X)`
- `backend/api/session.py` -- all vector_store calls
- `backend/services/matcher.py` -- `vector_store.get_by_session(X)`

### 2.3 Rewrite: `backend/services/session_store.py` (Redis-backed)

Replace the in-memory dictionary with a Redis-backed implementation. Same interface,
but now survives server restarts, auto-expires via Redis TTL, and is shared across
FastAPI + worker processes.

```python
# services/session_store.py (Redis-backed rewrite)

class SessionStore:
    def __init__(self, redis_url):
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.ttl = 3600  # 1 hour

    def create_session(self):
        session_id = str(uuid.uuid4())
        self.redis.setex(f"session:{session_id}", self.ttl, json.dumps({
            "created_at": time.time(),
            "messages": []
        }))
        return session_id

    def add_message(self, session_id, role, content):
        key = f"session:{session_id}"
        data = json.loads(self.redis.get(key) or "{}")
        messages = data.get("messages", [])
        messages.append({"role": role, "content": content})
        data["messages"] = messages
        self.redis.setex(key, self.ttl, json.dumps(data))

    def get_conversation_history(self, session_id):
        data = json.loads(self.redis.get(f"session:{session_id}") or "{}")
        return data.get("messages", [])

    def delete_session(self, session_id):
        self.redis.delete(f"session:{session_id}")

    def session_exists(self, session_id):
        return self.redis.exists(f"session:{session_id}")
```

### 2.4 New File: `backend/services/redis_client.py`

Async Redis client used across the application for:
- OTP storage: `otp:{email}` with 5-min TTL
- Rate limiting: `otp_rate:{email}` (3 req/5min), `otp_ip:{ip}` (10 req/hr)
- Session cache (via `session_store.py` above)

---

## Phase 3: API Routing Changes

### 3.1 New File: `backend/api/auth.py`

#### `POST /api/auth/request-otp`

```
Request:  { "email": "user@example.com" }
Rate limit: Max 3 per email/5min, Max 10 per IP/hour (Redis)
Action:   Generate 6-digit code, store in Redis (TTL 300s), send via Resend
Response: { "message": "OTP sent" }
```

#### `POST /api/auth/verify-otp`

```
Request:  { "email": "user@example.com", "code": "123456" }
Action:   Compare input against Redis key, upsert user in Postgres, create JWT
Response: { "token": "jwt...", "user_id": "uuid" }
```

### 3.2 Modify: `backend/api/upload.py`

**Current:** Parse -> Chunk -> Embed -> Store in ChromaDB -> Return session_id

**New:**
1. Require `Authorization: Bearer <jwt>` header
2. Calculate SHA-256 hash of uploaded file bytes
3. Query Postgres: `SELECT id FROM master_resumes WHERE user_id = ? AND file_hash = ?`
4. **If exists:** Return existing `resume_id` (skip parser + chunker + embedder)
5. **If new:** Parse, chunk, embed, store in ChromaDB keyed by new `resume_id`, insert into `master_resumes`
6. Return `{ "resume_id": "uuid", "filename": "...", "skills": [...] }`

### 3.3 Modify: `backend/api/match.py`

**Current:** Synchronous `await matcher.full_analysis(...)` with 180s timeout

**New:**
1. Require `Authorization: Bearer <jwt>` header
2. Validate `resume_id` exists in Postgres for this user
3. Create `tailoring_reports` row with `status: 'pending'`
4. Push JSON to Redis Stream `{ "report_id", "user_id", "resume_id", "jd_text" }`
5. Return `202 Accepted` with `{ "report_id": "uuid", "status": "pending" }`
6. **Remove** `/match/stream` endpoint entirely
7. **Remove** provider/model/api_key/base_url from `MatchRequest` model

**New endpoint: `GET /api/reports`**
- List all reports for the authenticated user
- Returns array of `{ id, status, jd_text (truncated), created_at, completed_at }`

**New endpoint: `GET /api/reports/{report_id}`**
- Fetch full report details for the authenticated user
- Returns `{ match_result, report, questions, rewrites, status }`

**New endpoint: `GET /api/reports/{report_id}/status`**
- Lightweight status check for polling
- Returns `{ "status": "processing" | "completed" | "failed" }`

### 3.4 Modify: `backend/api/chat.py`

- Require auth token
- Look up `resume_id` from the report being discussed
- Remove provider/model/apiKey/baseUrl parameters
- Use shared backend LLM key instead
- Keep streaming RAG chat functionality

### 3.5 Modify: `backend/main.py`

- Remove `cleanup_sessions()` background task (Redis TTL handles expiry)
- Remove `session_store` import cleanup logic
- Add `auth_router` at prefix `/api/auth`
- Add `prometheus-fastapi-instrumentator` middleware
- Add DB pool init in lifespan `startup` / shutdown `cleanup`
- Expand `GET /api/health` to check DB + Redis connectivity
- Register new report endpoints
- Add graceful shutdown for DB pool, Redis connections

---

## Phase 4: Background Worker

### 4.1 New File: `backend/worker.py`

Separate entry point running independently from FastAPI server.

```
Structure:
1. Connect to Redis (for streams + cache)
2. Connect to PostgreSQL pool
3. Initialize LLM service, vector_store, matcher
4. Consumer loop: for message in consumer -> await process_job(message)

async def process_job(payload):
    1. Update report status -> "processing" in Postgres
    2. Pull resume vectors from ChromaDB using resume_id
    3. Run matcher.compute_similarity() (CPU-bound, fast)
    4. Run llm_service.analyze_github_repos() if github data exists
    5. Run llm_service.generate_candidate_report() [re-engineered prompt]
    6. Run llm_service.generate_interview_questions() [re-engineered prompt]
    7. Run llm_service.generate_actionable_rewrites() [NEW]
    8. Save all results to Postgres (status -> "completed")
    9. Send email via Resend with magic link
```

### 4.2 Redis Stream Consumer Config

```python
# Worker reads from Redis Stream using consumer groups
# XREADGROUP GROUP tailoring-workers worker-1 STREAMS tailoring-jobs >

# Producer (in API endpoint)
await redis.xadd("tailoring-jobs", {
    "report_id": report_id,
    "user_id": user_id,
    "resume_id": resume_id,
    "jd_text": jd_text,
})

# Consumer (in worker.py)
while True:
    messages = await redis.xreadgroup(
        groupname="tailoring-workers",
        consumername="worker-1",
        streams={"tailoring-jobs": ">"},
        count=1,
        block=5000,
    )
    for stream, entries in messages:
        for msg_id, data in entries:
            await process_job(data)
            await redis.xack("tailoring-jobs", "tailoring-workers", msg_id)
```

### 4.3 Production Features in Worker

- **Retry with exponential backoff** on LLM call failures (3 retries, 1s/2s/4s)
- **Dead letter topic** for jobs that fail all retries
- **Correlation IDs** for tracing: API -> Redis Stream -> worker -> email
- **Structured logging** with job_id correlation

### 4.4 Modify: `backend/services/matcher.py`

- Keep `compute_similarity()` as-is (pure CPU, fast)
- Remove `full_analysis()` method (orchestration moves to worker)
- The worker will call individual methods directly

---

## Phase 5: LLM Prompt Re-Engineering

### 5.1 Modify: `backend/services/llm_service.py`

#### System Message Change

**Before:** `"You are a strict recruiter AI."`
**After:** `"You are a career coach helping candidates optimize their resume for a specific job description."`

#### `generate_candidate_report()` Rewrite

**Before prompt:** "You are a recruiter. Assess this candidate's fit."

**After prompt:**
```
You are a career coach. Analyze this candidate's resume against the job description.

1. Identify missing keywords that ATS (Applicant Tracking Systems) would look for
2. Suggest how to rephrase existing experience to better match this JD
3. Rate the ATS compatibility (not "fit" -- "compatibility")

Return ONLY JSON:
{
  "ats_score": 0,
  "missing_keywords": [],
  "keyword_suggestions": [
    {"original": "", "suggested_rewrite": ""}
  ],
  "summary": "",
  "strengths": [],
  "improvement_areas": []
}
```

#### New Method: `generate_actionable_rewrites()`

Takes the lowest-scoring resume chunks and generates 3 optimized bullet-point
alternatives per chunk.

```
Input: resume chunks, JD, match_result
Output: {"rewrites": [{"original_chunk": "", "rewrite_options": ["", "", ""]}]}
```

#### `generate_interview_questions()` Rewrite

**Before:** "Generate interview questions."

**After prompt:**
```
You are a mock interview coach. Given this candidate's resume and the job description,
generate interview questions that target the candidate's EXACT skill gaps.

Focus on questions the candidate is LIKELY to be asked about their weak areas.
Provide preparation tips for each question.

Return ONLY JSON:
{
  "technical": [],
  "behavioral": [],
  "gap_focused": [
    {"question": "", "why_likely": "", "prep_tips": ""}
  ]
}
```

#### `_call()` Method Update

Update the system message parameter from hardcoded "strict recruiter" to the
new career coach framing.

---

## Phase 6: Frontend UI/UX Flow

### 6.1 New File: `src/pages/AuthPage.jsx`

Simple email + OTP form:
- State 1: Enter email -> POST `/api/auth/request-otp` -> "Check your email" message
- State 2: Enter 6-digit code -> POST `/api/auth/verify-otp` -> store JWT in
  localStorage -> redirect to `/`

### 6.2 Modify: `src/pages/UploadPage.jsx`

Convert to 3-step wizard:

**Step 1 -- Input:**
- Upload resume PDF (keep existing file upload UI)
- Paste JD text (keep existing textarea)
- Remove: provider/model/API key selectors (backend uses shared key now)
- Remove: GitHub username input (move to optional settings or remove)

**Step 2 -- OTP:**
- If not authenticated (no JWT in localStorage), show inline OTP form
- If already authenticated, skip this step automatically

**Step 3 -- Success/Queued:**
- Replace loading spinner with:
  > "Analysis queued! We're processing your resume. You'll receive an email
  > with your results in about 2 minutes. You can also check your dashboard."
- "Go to Dashboard" button

### 6.3 Modify: `src/pages/Dashboard.jsx`

**Remove:**
- `POST /api/match` call and 180s timeout logic
- Auto-retry logic (2x retries on failure)
- "End Session" button
- Provider/model selection state

**Add:**
- `GET /api/reports` on mount -> show report history in sidebar ("My Portfolio")
- If URL has `reportId` param (from email magic link), fetch that report
- If report status is "processing", show polling status with estimated time
- If report status is "completed", show full results
- Rename "Candidate Match Score" -> "ATS Compatibility Score"
- Add prominent "Actionable Rewrites" section (before ReportSection)

**Keep:**
- PDF download functionality
- ChatSection (updated to use auth + resume_id)

### 6.4 Modify: `src/hooks/useBackendStatus.js`

- Remove 10-second auto-retry polling interval
- Change to single check on mount + manual refresh button
- Backend now accepts requests instantly, so no timeout concerns

### 6.5 Modify: `src/services/api.js`

**Remove:**
- `matchJD()` function
- `matchStream()` function
- Provider/model/apiKey/baseUrl parameters from remaining calls

**Add:**
- `requestOTP(email)` -> POST `/api/auth/request-otp`
- `verifyOTP(email, code)` -> POST `/api/auth/verify-otp`
- `fetchReports()` -> GET `/api/reports`
- `fetchReport(reportId)` -> GET `/api/reports/{reportId}`
- JWT token auto-injection in request headers
- `uploadResume(file)` -> updated to include auth header

### 6.6 Modify: `src/App.jsx`

```jsx
<Route path="/auth" element={<AuthPage />} />
<Route path="/dashboard" element={<Dashboard />} />
<Route path="/dashboard/:reportId" element={<Dashboard />} />
```

Add auth guard: redirect to `/auth` if no JWT in localStorage.

### 6.7 Component Updates

| Component           | Change                                                                 |
|---------------------|------------------------------------------------------------------------|
| `ScoreGauge.jsx`    | Label: "Match Score" -> "ATS Score"                                    |
| `ReportSection.jsx` | Add "Actionable Rewrites" as primary section                           |
| `QuestionsSection.jsx` | Add "gap_focused" questions with prep tips section                  |
| `BackendStatus.jsx` | Simplify to single check, not polling                                  |
| `ChatSection.jsx`   | Remove provider/model props, add auth header                           |
| `Loader.jsx`        | Keep as-is                                                             |

---

## Phase 7: Configuration & Deployment Updates

### 7.1 Modify: `backend/Dockerfile`

- Add worker as a separate target or use entrypoint script
- Worker runs `python worker.py` instead of uvicorn

### 7.2 Modify: `docker-compose.yml`

Add third service:
```yaml
worker:
  build: ./backend
  command: python worker.py
  env_file: .env
  depends_on:
    - backend
  restart: unless-stopped
```

Update backend service env_file to include all new env vars.
Keep ChromaDB volume for vector persistence.

### 7.3 Modify: `backend/Procfile`

```
web: uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
worker: python worker.py
```

### 7.4 Modify: `render.yaml`

Update to include worker process configuration. Note: Render free tier supports
one service, so worker may need a separate plan or alternative host.

---

## Execution Order

| Step | Phase | Files Touched                              | Depends On | Status |
|------|-------|--------------------------------------------|------------|--------|
| 1    | 1     | `requirements.txt`, `.env.example`, `docker-compose.yml` | Nothing | **DONE** |
| 2    | 2     | `db.py` (new), `vector_store.py` (modify)  | Step 1 | **DONE** |
| 3    | 2     | `session_store.py` (rewrite to Redis), `redis_client.py` (new) | Step 1 | **DONE** |
| 4    | 3.1   | `auth.py` (new)                            | Steps 2, 3 | **DONE** |
| 5    | 3.2   | `upload.py`                                | Steps 2, 4 | **DONE** |
| 6    | 3.3   | `match.py`                                 | Steps 2, 4 | **DONE** |
| 7    | 3.4   | `chat.py`                                  | Steps 2, 4 | **DONE** |
| 8    | 4     | `worker.py` (new), `matcher.py` refactor   | Steps 2, 6 | **DONE** |
| 9    | 5     | `llm_service.py`                           | Step 8 | **DONE** |
| 10   | 3.5   | `main.py`                                  | Steps 2-9 | **DONE** |
| 11   | 6.1   | `AuthPage.jsx` (new)                       | Step 4 | **DONE** |
| 12   | 6.2   | `UploadPage.jsx`                           | Steps 5, 11 | **DONE** |
| 13   | 6.3-6.7 | `Dashboard.jsx`, `useBackendStatus.js`, `api.js`, `App.jsx`, components | Steps 6-10 | **DONE** |
| 14   | 7     | `Dockerfile`, `docker-compose.yml`, `Procfile`, `render.yaml` | All above | |

---

## Security Notes

1. **Exposed GitHub token** in `frontend/recruiter-ui/.env` -- REVOKE IMMEDIATELY
2. LLM API key is now server-side only (never sent to frontend) -- major improvement
3. JWT tokens should have 1-hour TTL, stored in localStorage
4. Consider httpOnly cookies for production deployment
5. All new API endpoints require authentication (JWT validation middleware)
6. Rate limiting on OTP endpoints prevents abuse

---

## Production-Grade Features Checklist

- [x] Redis-backed session store (survives restarts, auto-expires)
- [x] PostgreSQL for persistent user/report data
- [x] Redis Streams for async job processing
- [x] Email notifications via Resend
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

---

## Files Summary

### New Files (7)
- `backend/services/db.py` -- PostgreSQL connection + models
- `backend/services/redis_client.py` -- Redis client
- `backend/api/auth.py` -- OTP endpoints
- `backend/worker.py` -- Redis Stream consumer worker
- `frontend/recruiter-ui/src/pages/AuthPage.jsx` -- Auth page
- `MIGRATION_PLAN.md` -- This file

### Modified Files (16)
- `backend/requirements.txt` -- Add new dependencies
- `backend/services/vector_store.py` -- session_id -> resume_id
- `backend/services/session_store.py` -- Rewrite to Redis-backed
- `backend/api/upload.py` -- Hash check, auth, resume_id
- `backend/api/match.py` -- Redis Stream producer, 202 response
- `backend/api/chat.py` -- Auth, shared LLM key
- `backend/api/github.py` -- session_id -> resume_id
- `backend/api/search.py` -- session_id -> resume_id
- `backend/api/session.py` -- Remove (or repurpose for report deletion)
- `backend/services/matcher.py` -- Remove full_analysis orchestration
- `backend/services/llm_service.py` -- New prompts, new methods
- `backend/main.py` -- Auth router, DB init, health checks, graceful shutdown
- `frontend/recruiter-ui/src/pages/UploadPage.jsx` -- 3-step wizard
- `frontend/recruiter-ui/src/pages/Dashboard.jsx` -- Report history, async flow
- `frontend/recruiter-ui/src/hooks/useBackendStatus.js` -- Remove polling
- `frontend/recruiter-ui/src/services/api.js` -- Auth functions, remove sync match
- `frontend/recruiter-ui/src/App.jsx` -- New routes, auth guard

### Deleted Files (0)
- None -- `session_store.py` is rewritten, not deleted
