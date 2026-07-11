# AI Resume Tailor -- Frontend

React 19 frontend for the AI Resume Tailor platform. Connects to a FastAPI backend with email OTP authentication, async job submission, and report history.

## Pages

- **AuthPage** (`/auth`) -- Email OTP sign-in (request code → verify → JWT)
- **UploadPage** (`/`) -- 3-step wizard: upload resume + paste JD → processing → queued
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
