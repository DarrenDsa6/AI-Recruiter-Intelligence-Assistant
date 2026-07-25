# AI Resume Tailor -- Frontend

React 19 frontend for the AI Resume Tailor platform. Connects to a FastAPI backend with email OTP authentication, async job submission, and report history.

## Pages

- **AuthPage** (`/auth`) -- Email OTP sign-in (request code -> verify -> JWT)
- **UploadPage** (`/`) -- Upload resume + paste JD, optional GitHub username, optional email notification
- **Dashboard** (`/dashboard/:reportId`) -- Report history sidebar, ATS score, skill gaps, actionable rewrites, interview questions, career coach chat

## Setup

```bash
npm install
npm start
```

Set `REACT_APP_API_URL` in `.env` to point to the backend (default: `http://localhost:8000`).

## Tech

- React 19 + React Router 7
- Tailwind CSS 3
- Create React App (CRA)
- ReactMarkdown + remark-gfm (chat rendering)

## Components

| Component | Description |
|-----------|-------------|
| `AuthPage.jsx` | OTP digit boxes, step indicator, resend cooldown, feature highlights |
| `UploadPage.jsx` | Drag-drop file upload (PDF/DOCX), JD textarea, GitHub username, email toggle |
| `Dashboard.jsx` | Report history sidebar, SVG ring gauge, collapsible sections, streaming chat |
| `GithubSection.jsx` | GitHub insights display (strong/weak signals, skill level, best project) |

## API Client

`services/api.js` handles:
- Cookie-based auth (httponly cookies)
- `requestOTP(email)` / `verifyOTP(email, code)`
- `uploadResumeAndJD(file)` / `startMatch(resumeId, jdText)`
- `fetchReports()` / `fetchReport(reportId)`
- Streaming chat via `POST /api/chat/stream`
- SSE status streaming via `GET /api/reports/:id/stream`

## Upload Response Types

The upload endpoint returns different response types based on validation:
- `UploadResponse` -- Successful upload with resume_id and skills
- `UploadDuplicateResponse` -- Same file already uploaded (deduplicated)
- `UploadRejectResponse` -- Document rejected (invalid type, not a resume, unsafe content, etc.)
