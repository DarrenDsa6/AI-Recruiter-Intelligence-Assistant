# AI Resume Tailor -- Frontend

React 19 frontend for the AI Resume Tailor platform. Connects to a FastAPI backend with email OTP authentication, async job submission, and report history.

## Pages

- **AuthPage** (`/auth`) -- Email OTP sign-in (request code -> verify -> JWT)
- **UploadPage** (`/`) -- 3-step wizard: upload resume + paste JD -> processing -> queued
- **Dashboard** (`/dashboard/:reportId`) -- Report history sidebar, ATS score, skill gaps, actionable rewrites, interview questions, career coach chat

## Setup

```bash
npm install
npm run dev
```

Set `VITE_API_URL` in `.env` to point to the backend (default: `http://localhost:8000`).

## Tech

- React 19 + React Router 7
- Tailwind CSS 3
- Vite

## Components

| Component | Description |
|-----------|-------------|
| `AuthPage.jsx` | OTP digit boxes, step indicator, resend cooldown, feature highlights |
| `UploadPage.jsx` | 3-step wizard with progress bar, drag-drop, character count |
| `Dashboard.jsx` | Report history sidebar, SVG ring gauge, collapsible sections with stagger animations |
| `ChatSection.jsx` | Streaming chat with JD + GitHub context, maximizable modal |
| `ScoreGauge.jsx` | SVG ring gauge for ATS compatibility score |
| `ReportSection.jsx` | Collapsible sections for strengths, gaps, recommendations |
| `QuestionsSection.jsx` | Gap-focused interview questions with prep tips |

## API Client

`services/api.js` handles:
- JWT injection in all requests
- `requestOTP(email)` / `verifyOTP(email, code)`
- `uploadResume(file)` / `startMatch(resumeId, jdText)`
- `fetchReports()` / `fetchReport(reportId)`
- Streaming chat via `POST /api/chat/stream`

## Upload Response Types

The upload endpoint returns different response types based on validation:
- `UploadResponse` -- Successful upload with resume_id and skills
- `UploadDuplicateResponse` -- Same file already uploaded (deduplicated)
- `UploadRejectResponse` -- Document rejected (invalid type, not a resume, unsafe content, etc.)
