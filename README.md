# AI Resume ATS Analyzer

AI Resume ATS Analyzer is a full-stack application that reads a resume, optionally compares it to a job description (JD), and produces an ATS-oriented score, detailed improvement feedback, skill-evidence validation, job-match insights, history, and a downloadable PDF report.

> **Important:** This project sends resume and JD text to the Groq API for structured extraction. It is **not** an entirely local/private analysis tool. Do not upload data you are not authorized to share.

## Table of contents

- [What the application does](#what-the-application-does)
- [System architecture](#system-architecture)
- [End-to-end request flow](#end-to-end-request-flow)
- [Scoring and matching logic](#scoring-and-matching-logic)
- [Project structure](#project-structure)
- [Frontend](#frontend)
- [Backend](#backend)
- [API reference](#api-reference)
- [Data model and Supabase](#data-model-and-supabase)
- [Configuration](#configuration)
- [Local setup](#local-setup)
- [Security, privacy, and limitations](#security-privacy-and-limitations)
- [Troubleshooting](#troubleshooting)

## What the application does

1. A user creates an account or signs in using Supabase email/password authentication or Google OAuth.
2. The user uploads a resume (`.pdf`, `.docx`, or `.doc`, maximum 5 MB) and may paste/upload a JD.
3. The backend extracts text from the resume. PDF extraction tries `pdfplumber` first and falls back to `PyPDF2`; DOCX extraction reads paragraphs, tables, and hyperlinks.
4. Groq (`llama-3.3-70b-versatile`) converts the resume into structured JSON: contact fields, summary, skills, experience, education, projects, action verbs, and keywords. If a JD was provided, Groq also extracts required/preferred skills and keywords from it.
5. spaCy and Sentence Transformers perform local NLP work: named-entity/noun-phrase analysis and semantic-similarity calculations.
6. The scoring engine calculates an overall score out of 100, issue-level feedback, strengths, missing/matched JD keywords, and whether listed skills are demonstrated in projects or experience.
7. The result is shown in Streamlit, persisted in Supabase history when server-side Supabase credentials are configured, and can be exported as a PDF.

## System architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Browser / Streamlit UI (port 8501)                                  │
│ Login, upload, JD input, results dashboard, history, PDF download   │
└───────────────┬─────────────────────────────────────────────────────┘
                │ HTTPS/HTTP + Bearer access token
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ FastAPI backend (port 8000)                                         │
│ JWT verification • validation • API routes • PDF response           │
└───────┬──────────────────┬─────────────────────┬────────────────────┘
        │                  │                     │
        ▼                  ▼                     ▼
┌───────────────┐  ┌──────────────────┐  ┌───────────────────────────┐
│ Resume parser │  │ Analysis pipeline│  │ Report generator / PDF     │
│ PDF/DOCX text │  │ scorer + feedback│  │ ReportLab (active endpoint)│
└───────────────┘  └──────┬───────────┘  └───────────────────────────┘
                          │
        ┌─────────────────┼───────────────────────┐
        ▼                 ▼                       ▼
┌────────────────┐ ┌────────────────────┐ ┌──────────────────────────┐
│ Groq API       │ │ spaCy + MiniLM     │ │ Supabase                 │
│ JSON extraction│ │ NER, phrases,      │ │ Auth/JWKS + analyses     │
│ resume + JD    │ │ embeddings/matching│ │ table/history            │
└────────────────┘ └────────────────────┘ └──────────────────────────┘
```

### Component responsibilities

| Layer | Technology | Responsibility |
|---|---|---|
| Presentation | Streamlit | Page navigation, sign-in UI, upload/JD form, metrics, feedback widgets, history and download actions. |
| API | FastAPI | Auth-protected endpoints, model startup/loading, CORS, request/response validation, error mapping. |
| Parsing | pdfplumber, PyPDF2, python-docx, Groq | Converts files into text, then converts free text into predictable structured fields. |
| NLP/ML | spaCy, Sentence Transformers, NumPy, RapidFuzz | Semantic similarity, JD skill-gap candidates, keyword normalization, fuzzy matching. |
| Business logic | Python services | ATS component scores, score penalties/bonuses, issue detection, recommendations. |
| Identity/storage | Supabase | Email/password and Google OAuth; server verifies JWT; analysis history is stored in `analyses`. |
| Reporting | ReportLab; Jinja2/WeasyPrint fallback utilities | Builds the endpoint's PDF report. Legacy HTML-report helpers also exist. |

## End-to-end request flow

### Resume analysis

```text
User → Streamlit → POST /api/v1/analyze-resume
     → Bearer JWT verification
     → resume file validation (size + extension + basic signature)
     → PDF/DOCX text extraction
     → Groq resume parsing
     → [if JD exists] Groq JD parsing + semantic/keyword comparison
     → skill validation + score calculation + feedback engine
     → save result to Supabase (non-blocking)
     → JSON response → Streamlit dashboard
```

### Authentication and history

```text
Streamlit → Supabase Auth → access token → FastAPI Authorization header
FastAPI → verifies token using Supabase JWKS (RS256/ES256) or JWT secret (HS256)
FastAPI → Supabase REST API using service-role key → per-user analysis records
```

The frontend never chooses the backend `user_id`; the backend derives it from the verified JWT's `sub` claim. History queries and deletes are additionally filtered by this ID.

## Scoring and matching logic

### Component scores

Each component is returned in its own maximum range. The overall score is then normalized to 0–100.

| Component | Maximum | What is checked |
|---|---:|---|
| Formatting | 20 | Experience, education, skills, summary and project sections; bullet count; completeness of key sections. |
| Keywords | 25 | Number of extracted resume keywords and skills; optional fuzzy overlap with JD keywords. |
| Content | 25 | Action verbs, measurable achievements (percentages, money, counts, etc.), grammar-result penalty. |
| Skill validation | 15 | How many claimed skills are found exactly or semantically in project/experience text. |
| ATS compatibility | 15 | Location/privacy deductions, heavy box-drawing/special characters, very short sections, and a small experience+skills bonus. |

The overall formula currently uses:

```text
skills_keywords = 60% keyword score + 40% skill-validation score
base score      = 40% skills_keywords + 30% content
                  + 15% formatting + 15% ATS compatibility
```

It then applies configured logic: grammar/location penalties (when those components are available), a +1/+2 bonus for strong skill validation, a +1 grammar bonus if no errors are reported, and JD-keyword penalties of 5/10/15 when the missing-keyword ratio is high.

### JD matching

- **Keyword matching:** aliases such as `reactjs → react`, `node → node.js`, and `ml → machine learning` are normalized. RapidFuzz token-sort matching uses an 80 threshold.
- **Semantic similarity:** MiniLM embeddings are created for the first 5,000 characters of resume and JD, then cosine similarity is calculated.
- **JD match percentage:** `(60% keyword overlap + 40% semantic similarity) × 100`.
- **Skills gap:** spaCy entities/noun chunks found in the JD are compared with resume skills using aliases and fuzzy matching; this is a candidate list, not proof that a skill is mandatory.

### Skill validation

For every parsed skill, the engine first performs an exact case-insensitive text check against every project and all experience text. If not found, it compares embeddings; similarity `>= 0.6` counts as evidence. The response lists validated skills with associated project/experience evidence and separately lists unvalidated skills.

### Feedback

`feedback_engine.py` turns structural and score signals into typed issues. Every issue has a title, severity, ATS impact, explanation, location, fix instructions, actionable items, and an example improvement. The UI groups feedback by severity and converts action items into a priority list.

## Project structure

```text
ai-resume-ats/
├── backend/
│   ├── main.py                     # FastAPI app, model lifecycle, CORS, router registration
│   ├── api/
│   │   ├── routes.py               # Protected HTTP endpoints
│   │   └── auth.py                 # Supabase JWT verification
│   ├── core/config.py              # Environment variables, model names, limits, scoring constants
│   ├── database/supabase_db.py     # Supabase REST persistence for analysis history
│   ├── models/schemas.py           # Pydantic API request/response shapes
│   ├── services/
│   │   ├── resume_parser.py        # File validation and PDF/DOCX extraction
│   │   ├── groq_parser.py          # Groq prompts, calls, JSON cleanup/validation
│   │   ├── resume_analyzer.py      # Orchestrates the complete analysis pipeline
│   │   ├── ats_scorer.py           # Component/overall scoring and skill validation
│   │   ├── jd_matcher.py           # JD semantic, keyword, and gap analysis
│   │   ├── feedback_engine.py      # Detailed issue detection
│   │   ├── recommendation_engine.py# Reusable priority recommendation builder
│   │   ├── report_generator.py     # HTML report/template context helper
│   │   └── pdf_export.py           # ReportLab PDF endpoint + HTML-PDF fallback helpers
│   ├── templates/                  # Jinja HTML report templates (legacy/helper path)
│   └── utils/
│       ├── matching.py             # Skill aliases + RapidFuzz matching
│       └── file_utils.py           # Logging, errors, fallbacks, default results
├── frontend/
│   ├── streamlit_app.py            # UI entry point, nav, session/auth state
│   ├── views/                      # landing, scorer, history, resources pages
│   ├── components/                 # Reusable result-display widgets
│   ├── services/                   # FastAPI client and Supabase auth client
│   ├── assets/styles.css           # Global styles and responsive rules
│   └── .streamlit/                 # Streamlit configuration and local secrets
├── jupyter notebooks/              # EDA, embeddings, BERT experimentation; not runtime code
├── requirements.txt                # Combined dependency list
└── README.md                       # This document
```

## Frontend

`frontend/streamlit_app.py` is the frontend entry point. It configures Streamlit, initializes session state, exchanges a Google OAuth callback `code`, loads CSS, renders sidebar authentication/navigation, and routes to the active view.

| File/group | Smallest responsibility |
|---|---|
| `views/landing.py` | Product introduction, feature overview and navigation to scorer. |
| `views/scorer.py` | Resume/JD input, calls analysis API, stores active result in session, triggers dashboard/PDF. JD text can be pasted or read from an uploaded JD file. |
| `views/history.py` | Calls history endpoint, renders saved score breakdowns, deletes records. |
| `views/resources.py` | Displays resume/ATS learning content. |
| `services/api_client.py` | Central HTTP client: backend URL resolution, bearer headers, analyze/history/delete/PDF functions. Local default is `http://127.0.0.1:8000`. |
| `services/supabase_client.py` | Reads config from environment or Streamlit secrets; provides password auth, signup, OAuth URL, callback exchange, and signout. |
| `components/dashboard.py` | Composes the result dashboard. |
| `score_display.py` | Overall score and five score-breakdown visuals. |
| `strengths_issues.py` | Strengths and critical-issue sections. |
| `detailed_feedback.py` | Severity-grouped issue cards. |
| `skill_validation.py` | Validated/unvalidated skills and evidence. |
| `jd_comparison.py` | JD match score, matched/missing keywords and gap list. |
| `action_items.py` | Consolidates fixes into actionable tasks. |
| `recommendations.py` | Displays recommendation cards. |
| `_helpers.py` | Shared color, emoji and severity presentation helpers. |

## Backend

### Startup

`backend/main.py` uses FastAPI's lifespan hook to load, once per process:

- spaCy model `en_core_web_md`; if absent, it tries `en_core_web_sm`.
- Sentence Transformer `all-MiniLM-L6-v2` by default, configurable through `SENTENCE_TRANSFORMER_MODEL`.

These objects are placed in `app.state.nlp` and `app.state.embedder`, avoiding a model reload on every analysis request. Interactive API documentation is exposed at `/docs` and `/redoc`.

### Parsing detail

- File size is capped at **5 MB**.
- Only filenames with `.pdf`, `.docx`, or `.doc` pass validation. PDFs must start with `%PDF-`; DOCX files must start with ZIP bytes (`PK`).
- `.doc` passes initial validation but the extractor deliberately returns an error because legacy Word parsing is not implemented. Convert it to PDF or DOCX first.
- Image-only/scanned PDFs cannot be read because there is no OCR pipeline; the user needs a PDF with selectable text.
- Text is not permanently written to local files by the parser. Backend logs are written under `backend/logs/`.

### Groq parser detail

`groq_parser.py` limits each submitted resume/JD to the first **12,000 characters**, uses deterministic temperature `0.0`, requests JSON only, strips Markdown code fences if needed, validates expected keys, and retries once if Groq returns invalid JSON. A valid `GROQ_API_KEY` is necessary for the analysis endpoint because structured parsing starts with Groq.

### Pydantic response shape

`AnalysisResponse` includes these key fields:

```json
{
  "ATS_score": 0.0,
  "component_scores": {
    "formatting": 0.0,
    "keywords": 0.0,
    "content": 0.0,
    "skill_validation": 0.0,
    "ats_compatibility": 0.0
  },
  "issues_summary": [],
  "detailed_feedback": [],
  "jd_match_analysis": null,
  "skill_validation_details": null,
  "matched_keywords": [],
  "missing_keywords": [],
  "strengths": [],
  "interpretation": ""
}
```

`ATS_score` and `ats_score` both exist for backward compatibility and contain the same overall value.

## API reference

Every endpoint below except `/` and `/api/v1/health` requires:

```http
Authorization: Bearer <Supabase access token>
```

| Method and path | Input | Output / behavior |
|---|---|---|
| `GET /` | none | API identity, version and endpoint list. |
| `GET /api/v1/health` | none | Confirms that spaCy and embedding models are loaded. |
| `POST /api/v1/analyze-resume` | Multipart: `resume` file, optional `job_description` text | Runs full analysis; attempts to save history without failing an otherwise successful response. |
| `GET /api/v1/history` | JWT | Returns analyses belonging to token owner, newest first. |
| `DELETE /api/v1/history/{analysis_id}` | JWT | Deletes only a record whose ID and `user_id` match the caller. |
| `POST /api/v1/generate-pdf` | `AnalysisResponse` JSON | Returns `application/pdf` attachment named `ats_report.pdf`. |
| `GET /api/v1/history/{analysis_id}/pdf` | JWT | Loads the caller's saved analysis and returns a PDF report. |

## Data model and Supabase

The backend writes via Supabase REST using `SUPABASE_KEY` (a service-role key). It expects an `analyses` table with at least these fields:

| Column | Purpose |
|---|---|
| `id` | Unique analysis identifier. |
| `user_id` | Supabase Auth user UUID. |
| `filename` | Uploaded resume filename. |
| `ats_score` | Overall ATS score. |
| `keyword_match` | JD match percentage or 0 without a JD. |
| `missing_keywords` | Array/JSON list. |
| `created_at` | ISO UTC timestamp. |
| `analysis_result` | Complete JSON result used for history display/PDF regeneration. |

Suggested SQL schema (adapt types/permissions to your Supabase setup):

```sql
create table public.analyses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  filename text not null,
  ats_score numeric not null default 0,
  keyword_match numeric not null default 0,
  missing_keywords jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  analysis_result jsonb not null default '{}'::jsonb
);

create index analyses_user_created_idx
  on public.analyses (user_id, created_at desc);
```

The application itself uses the service role to write/read history and filters by the verified user ID. You should still enable Row Level Security and define appropriate policies if the table is ever accessed directly from a client.

## Configuration

Create a project-root `.env`. Never commit it.

```dotenv
# Required for resume/JD parsing
GROQ_API_KEY=your_groq_key

# Required by backend JWT verification and server-side history persistence
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key

# Required only when Supabase issues HS256 JWTs; asymmetric projects use JWKS via URL
SUPABASE_JWT_SECRET=your_jwt_secret

# Used by frontend authentication (can also live in Streamlit secrets)
SUPABASE_ANON_KEY=your_anon_key

# Optional: defaults to all-MiniLM-L6-v2
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2

# Optional: URL Streamlit returns to after Google sign-in
AUTH_REDIRECT_URL=http://localhost:8501
```

For Streamlit deployment/local frontend configuration, `frontend/.streamlit/secrets.toml` can contain:

```toml
[backend]
url = "http://127.0.0.1:8000"

[supabase]
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your_anon_key"

[google_oauth]
redirect_uri = "http://localhost:8501"
```

Configure the same redirect URL in Supabase Auth settings and, for Google login, configure Google as a Supabase OAuth provider.

### CORS note

`backend/core/config.py` currently permits one configured Streamlit deployment origin. For local frontend-to-backend browser deployments, add the exact frontend origin (for example `http://localhost:8501`) to `ALLOWED_ORIGINS`; do not use a wildcard with credentialed requests.

## Local setup

### Prerequisites

- Python 3.10+ recommended
- A Groq API key
- A Supabase project for sign-in and history
- Internet access on first run to download `all-MiniLM-L6-v2`

### Install

```powershell
cd ai-resume-ats
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download en_core_web_md
```

If the medium spaCy model is unavailable, the backend attempts `en_core_web_sm`; install it with `python -m spacy download en_core_web_sm`.

On Linux, WeasyPrint may require Cairo/Pango system packages. The primary API PDF route uses ReportLab, but WeasyPrint remains available to the HTML report helper/fallback path.

### Run

Open two terminals in the repository root, with the virtual environment activated in each:

```powershell
# Terminal 1: API
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

```powershell
# Terminal 2: UI
streamlit run frontend/streamlit_app.py
```

Open `http://localhost:8501`. Test backend readiness at `http://127.0.0.1:8000/api/v1/health` and API docs at `http://127.0.0.1:8000/docs`.

## Security, privacy, and limitations

- Resume/JD text is sent to Groq during analysis. The first 12,000 characters are sent; keep this in mind for privacy and for very long resumes.
- The frontend sends a Supabase bearer token to the backend. The backend verifies the signature/audience before using its user ID.
- Keep `SUPABASE_KEY` server-only. It is a service-role credential and bypasses Supabase RLS; never put it in Streamlit secrets sent to a public client.
- Keep `.env` and `frontend/.streamlit/secrets.toml` out of Git. Both paths are already ignored.
- Analysis history is best-effort: a Supabase save failure is logged but does not fail the scoring response.
- PDF/DOCX text extraction does not OCR scanned documents. Legacy `.doc` is currently rejected after upload validation.
- The score is an internal heuristic, not the behavior of any specific employer ATS or a hiring decision. Groq extraction and semantic matching can make mistakes; review feedback before changing a resume.
- `recommendation_engine.py` and Jinja templates are reusable code but are not invoked by the current `analyze_resume` route; current feedback comes from `feedback_engine.py` and the endpoint PDF comes from `generate_analysis_pdf`.
- The project includes experimental notebooks, but runtime analysis uses the configured spaCy and Sentence Transformer models, not a locally fine-tuned BERT artifact.

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `GROQ_API_KEY environment variable not set` | Missing Groq key | Add `GROQ_API_KEY` to root `.env`, then restart backend. |
| Backend startup fails loading spaCy | Model not installed | Run `python -m spacy download en_core_web_md`; or install the small fallback model. |
| Frontend says backend cannot be reached | API not running or wrong URL | Start Uvicorn on port 8000; update `[backend].url` in secrets for deployments. |
| `401 Missing Authorization` | User not signed in / token absent | Sign in through the sidebar and retry. |
| `401 Token expired` | Expired Supabase session | Sign out and sign in again. |
| `422 Could not read or parse` | Oversized, corrupted, scanned, or unsupported document | Use a selectable-text PDF/DOCX under 5 MB. Convert `.doc` first. |
| OAuth returns to the app but login fails | Redirect URLs differ | Make `AUTH_REDIRECT_URL`, Streamlit secret, and Supabase allow-list identical. |
| History is empty after analysis | Backend lacks service-role configuration or Supabase write failed | Set `SUPABASE_URL` + `SUPABASE_KEY`; inspect `backend/logs/ats_scorer.log`. |
| Browser CORS error | Frontend origin not allowed | Add the exact UI origin to `ALLOWED_ORIGINS` in `backend/core/config.py`. |

## Development notes

- No automated test suite is currently present in the repository. Before deployment, add API tests for authentication, file validation, score calculation, and Supabase error behavior.
- `requirements.txt` combines frontend and backend dependencies. Pin exact versions for reproducible production deployments.
- The first transformer-model load can take noticeable time and downloads model weights to the local cache; later starts reuse the cache.
