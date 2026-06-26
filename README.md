# AI Recruiter Intelligence Assistant

An end-to-end AI-powered candidate screening platform. Upload a resume, paste a job description, and get a structured match analysis with scores, skill gaps, GitHub insights, interview questions, and a persistent streaming chat over the resume context.

---

## Features

- **Resume Ingestion** — Upload PDF/DOCX; text is extracted, chunked, and embedded into ChromaDB per session
- **GitHub Integration** — Fetch public repos, READMEs, languages for deeper candidate insight. Supports authenticated requests via frontend token input or `GITHUB_TOKEN` env var for higher rate limits.
- **Job Match Engine** — Two-layer evaluation: deterministic skill matching (semantic + regex) weighted at 70%, plus LLM-powered reasoning for report and questions
- **Structured Dashboard** — Circular score gauge, skill tag clouds (matched/missing), GitHub signals, AI report, accordion interview questions
- **Streaming Chat** — Resume-aware conversational follow-ups with full markdown rendering and persistent session history. Features a full-screen popup mode for focused conversation.
- **PDF Export** — Download the full report as a pixel-perfect A4 PDF
- **Session Isolation** — Each candidate is a unique session; closing it erases all vectors and history

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, React Router 7, Tailwind CSS 3, Framer Motion |
| **Backend** | FastAPI, Python 3.11, Uvicorn |
| **LLM** | Mistral Large 3 (675B) via NVIDIA API |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 |
| **Semantic Matching** | BAAI/bge-small-en-v1.5 |
| **Vector DB** | ChromaDB (persistent) |
| **PDF Export** | html2canvas-pro + jsPDF |
| **Markdown Rendering** | react-markdown + remark-gfm |
| **File Parsing** | PyMuPDF (PDF), python-docx (DOCX) |
| **External APIs** | GitHub REST API (optional auth via token) |

---

## Scoring Formula

```
final_score = (skill_score × 0.7) + (document_score × 0.3)
skill_score = (required_match × 0.7) + (optional_match × 0.3)
document_score = cosine_similarity(JD_embedding, resume_embedding)
```

---

## Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI app, CORS, lifespan cleanup
│   ├── api/
│   │   ├── upload.py            # POST /api/upload
│   │   ├── match.py             # POST /api/match, /api/match/stream
│   │   ├── chat.py              # POST /api/chat/stream
│   │   └── session.py           # DELETE /api/session/end/{id}
│   ├── services/
│   │   ├── parser.py            # PDF/DOCX text extraction
│   │   ├── chunker.py           # 500-char text windows
│   │   ├── embedding_service.py # Embedding generation + cache
│   │   ├── vector_store.py      # ChromaDB operations
│   │   ├── session_store.py     # In-memory session + chat history
│   │   ├── skills.py            # Regex-based skill extraction
│   │   ├── semantic_matcher.py  # Semantic skill matching
│   │   ├── weighted_skill_gap_analyzer.py  # Scoring engine
│   │   ├── jd_skill_classifier.py  # Required vs optional
│   │   ├── matcher.py           # Orchestrator
│   │   ├── llm_service.py       # Mistral via NVIDIA API
│   │   └── github_service.py    # GitHub API client
│   ├── data/                    # skills.json, skill_aliases.json
│   ├── services/.env            # LLM_API_KEY
│   └── .env.example
│
├── frontend/recruiter-ui/
│   ├── src/pages/
│   │   ├── UploadPage.jsx       # Resume + JD + GitHub input
│   │   └── Dashboard.jsx        # Scores, skills, report, chat
│   ├── src/components/
│   │   ├── ScoreGauge.jsx       # Circular SVG gauge
│   │   ├── SkillsSection.jsx    # Required / Matched / Missing tags
│   │   ├── GithubSection.jsx    # GitHub signals panel
│   │   ├── ReportSection.jsx    # AI strengths/weaknesses/recommendation
│   │   ├── QuestionsSection.jsx # Accordion interview questions
│   │   └── ChatSection.jsx      # Streaming markdown chat
│   ├── src/utils/
│   │   └── pdfGenerator.js      # PDF export
│   └── tailwind.config.js
```

---

## Running Locally

```bash
# Backend
cd backend
pip install -r requirements.txt
# Set LLM_API_KEY in services/.env
uvicorn main:app --reload --port 8000

# Frontend
cd frontend/recruiter-ui
npm install
npm start
```

Open [http://localhost:3000](http://localhost:3000).

---

## Author

**Darren Dsa** — [GitHub](https://github.com/DarrenDsa6)
