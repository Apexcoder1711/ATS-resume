# Minor Project Report and Presentation Guide

## Project title

**AI Resume ATS Analyzer: An Intelligent Resume Screening and Job-Description Matching System**

## Project team

| Member | Suggested presentation responsibility |
|---|---|
| **Ankita** | Introduction, problem statement, objectives, frontend and user flow |
| **Prachi** | Backend architecture, resume parsing, AI/NLP pipeline |
| **Suchitra** | Scoring logic, database/security, output, conclusion and future scope |

---

# Part A — Project Report

## 1. Abstract

Recruiters often receive many resumes for one job opening. Applicant Tracking Systems (ATS) help them filter resumes by checking keywords, skills, formatting, and relevance to the job description. However, students and job seekers usually do not know why their resume may be rejected or which changes will improve it.

**AI Resume ATS Analyzer** is a web application that analyzes a resume and optionally compares it with a job description. The system accepts PDF/DOCX resumes, extracts their text, uses Artificial Intelligence to identify structured information such as skills, projects, experience, education, keywords, and action verbs, and calculates an ATS-oriented score out of 100. It also identifies missing job-description keywords, validates whether claimed skills are supported by projects or experience, generates detailed improvement suggestions, stores past analyses for authenticated users, and exports an ATS report as a PDF.

The project uses **Streamlit** for the user interface, **FastAPI** for backend APIs, **Groq Llama 3.3** for structured resume/JD extraction, **spaCy** and **Sentence Transformers** for NLP and semantic comparison, and **Supabase** for authentication and analysis history.

## 2. Problem statement

Job seekers often create resumes without knowing whether the resume is readable by an ATS or aligned with a particular job role. Manual review is slow and subjective. A system is needed that can:

- read a resume automatically;
- identify important sections, skills, keywords and achievements;
- compare resume content with a job description;
- provide a clear score and actionable feedback; and
- maintain secure user-wise analysis history.

## 3. Objectives

1. To accept and extract text from resume documents.
2. To identify resume information such as skills, projects, experience, education, keywords and action verbs.
3. To calculate an ATS-oriented score based on multiple resume quality factors.
4. To compare a resume with a supplied job description.
5. To identify matched and missing keywords and potential skill gaps.
6. To check whether listed skills are supported by project or experience evidence.
7. To generate practical, priority-based improvement feedback.
8. To provide secure login, saved history and PDF report export.

## 4. Scope

### Included in the project

- User sign-up/sign-in through email/password and Google OAuth support.
- Resume upload with a maximum size of 5 MB.
- PDF and DOCX text extraction; DOC upload is detected but users are asked to convert it because legacy DOC extraction is not implemented.
- Resume analysis with score, strengths, issues and action items.
- Optional job-description comparison.
- User-specific history storage.
- Downloadable PDF report.

### Not included / limitations

- Image-only or scanned PDFs are not supported because OCR is not implemented.
- The score is a project heuristic; it is not the exact score used by any company’s proprietary ATS.
- AI extraction can occasionally miss or misclassify information, so users should review suggestions.
- Resume/JD text is sent to Groq for structured extraction; therefore it is not a fully offline system.

## 5. Technology stack

| Category | Technology | Use in the project |
|---|---|---|
| Programming language | Python | Backend, frontend and AI logic |
| Frontend | Streamlit | Interactive web interface and dashboard |
| Backend | FastAPI | REST APIs, validation, authentication integration |
| AI/LLM | Groq API with Llama 3.3 70B Versatile | Converts resume/JD text to structured JSON |
| NLP | spaCy | Named entities and noun phrases for skill-gap analysis |
| Semantic AI | Sentence Transformers (`all-MiniLM-L6-v2`) | Embeddings and cosine similarity |
| Fuzzy matching | RapidFuzz | Matches skill variants and near-equivalent keywords |
| Database/Auth | Supabase | User login, JWT tokens and analysis history |
| File parsing | pdfplumber, PyPDF2, python-docx | PDF/DOCX text extraction |
| PDF generation | ReportLab | Final downloadable ATS report |
| Styling | CSS | Streamlit UI appearance and responsive design |

## 6. System architecture

```text
                         ┌──────────────────────────┐
                         │        User / Browser    │
                         └────────────┬─────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Streamlit Frontend                                                   │
│ Login • Resume Upload • JD Input • Dashboard • History • PDF Button │
└──────────────┬──────────────────────────────────────────────────────┘
               │ REST API request + Supabase Bearer JWT
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ FastAPI Backend                                                      │
│ Token verification • File validation • API routes • Response models │
└───────┬────────────────────┬───────────────────────┬────────────────┘
        │                    │                       │
        ▼                    ▼                       ▼
┌───────────────┐   ┌───────────────────────┐  ┌─────────────────────┐
│ Resume Parser │   │ AI and NLP Pipeline   │  │ PDF Report Generator│
│ PDF/DOCX text │   │ score + feedback      │  │ ReportLab           │
└───────────────┘   └───────┬───────────────┘  └─────────────────────┘
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
       ┌────────────┐ ┌─────────────┐ ┌────────────────┐
       │ Groq LLM   │ │ spaCy +     │ │ Supabase       │
       │ Resume/JD  │ │ MiniLM      │ │ Auth + History │
       │ JSON parse │ │ Matching    │ │ Database       │
       └────────────┘ └─────────────┘ └────────────────┘
```

## 7. Detailed workflow diagram

```text
START
  │
  ▼
User signs in / creates account
  │
  ▼
User uploads resume and optionally enters job description
  │
  ▼
Frontend sends multipart request + JWT token to FastAPI
  │
  ▼
Backend verifies Supabase JWT
  │
  ├── Invalid token ──► Show unauthorized error ──► END
  │
  ▼
Validate file extension, signature and size (≤ 5 MB)
  │
  ├── Invalid file ──► Show file error ──► END
  │
  ▼
Extract resume text
  │       ├─ PDF: pdfplumber → PyPDF2 fallback
  │       └─ DOCX: python-docx paragraphs/tables/links
  ▼
Groq parses resume into structured JSON
  │
  ├── If JD provided: Groq parses JD into skills + keywords
  │                    │
  │                    ▼
  │             Calculate semantic similarity,
  │             keyword match, missing keywords, skill gap
  ▼
Validate claimed skills against projects and experience
  │
  ▼
Calculate five component scores and overall ATS score
  │
  ▼
Generate strengths, detailed issues and actionable feedback
  │
  ▼
Save result in Supabase history (best effort)
  │
  ▼
Show dashboard; user may download PDF report
  │
  ▼
END
```

## 8. Modules and their role

| Module | Main files | What it does |
|---|---|---|
| User interface | `frontend/streamlit_app.py`, `frontend/views/` | Manages navigation, login state, upload form, history and resources. |
| UI result components | `frontend/components/` | Displays score, breakdown, JD comparison, strengths, feedback, skills and action items. |
| API client | `frontend/services/api_client.py` | Calls backend endpoints and adds bearer token. |
| Authentication client | `frontend/services/supabase_client.py` | Performs password login/signup, Google OAuth and session handling. |
| API layer | `backend/main.py`, `backend/api/routes.py` | Starts FastAPI, loads models, exposes endpoints and maps errors. |
| JWT security | `backend/api/auth.py` | Verifies Supabase-issued JWT and gets authenticated user ID. |
| File parser | `backend/services/resume_parser.py` | Validates and extracts PDF/DOCX content. |
| LLM parser | `backend/services/groq_parser.py` | Prompts Groq and validates returned JSON. |
| Analysis orchestrator | `backend/services/resume_analyzer.py` | Connects parser, matcher, scorer and feedback engine. |
| ATS scoring | `backend/services/ats_scorer.py` | Calculates component and final scores; validates skills. |
| JD matcher | `backend/services/jd_matcher.py` | Measures similarity, keyword overlap and missing skill candidates. |
| Feedback engine | `backend/services/feedback_engine.py` | Creates issue cards with severity and fixes. |
| Database | `backend/database/supabase_db.py` | Saves, retrieves and deletes user-wise analyses. |
| Report service | `backend/services/pdf_export.py` | Creates downloadable PDF report. |

## 9. Resume parsing and AI extraction

After text extraction, Groq is instructed to return only valid JSON. The main extracted fields are:

```text
Name, email, phone, LinkedIn, GitHub
Professional summary
Skills
Experience: job title, company, dates, duration, description
Education
Certifications
Projects: title, description, technologies
Action verbs
ATS keywords
```

When a JD is supplied, the system extracts job title, required skills, preferred skills, experience/education requirements, responsibilities and keywords.

The input is limited to the first 12,000 characters for each Groq request, and the response is retried once if it is not valid JSON.

## 10. ATS scoring methodology

The project provides five component scores:

| Component | Maximum score | Measurement details |
|---|---:|---|
| Formatting | 20 | Presence of experience, education, skills, summary and projects; bullet points; section completeness. |
| Keywords | 25 | Quantity of skills/keywords; optional match with JD terms. |
| Content | 25 | Action verbs, measurable achievements (for example %, money, users, projects), grammar-result data. |
| Skill validation | 15 | Whether a listed skill is supported by project or experience text. |
| ATS compatibility | 15 | Privacy/location signals, excessive special characters, short/incomplete sections. |

### Overall score formula

```text
Skills and keywords score = 60% keyword score + 40% skill-validation score

Base ATS score = 40% skills/keywords
               + 30% content
               + 15% formatting
               + 15% ATS compatibility

Final score = Base score + applicable bonuses − applicable penalties
```

The score is clamped between 0 and 100. Examples of extra logic include a bonus for excellent skill validation, a bonus when grammar data reports no errors, and a penalty when a high percentage of JD keywords is missing.

## 11. Job-description matching methodology

1. Skills such as `ReactJS` and `React`, or `Node` and `Node.js`, are normalized with a skill-alias dictionary.
2. RapidFuzz compares normalized resume and JD terms. A similarity threshold of 80 is used for keyword matching.
3. Sentence Transformer embeddings are created for resume and JD text.
4. Cosine similarity gives a semantic relevance value from 0 to 1.
5. JD match percentage is calculated as:

```text
JD Match % = (0.60 × keyword overlap + 0.40 × semantic similarity) × 100
```

6. spaCy noun phrases/entities from the JD are compared to resume skills to identify possible missing skills.

## 12. Skill-validation methodology

For every skill listed in a resume:

1. The system first searches project and experience text directly, ignoring case.
2. If an exact match is not available, the system compares the skill embedding with project/experience embedding.
3. A semantic similarity of at least `0.6` is considered evidence.
4. The output shows validated skills along with matching projects or the Experience Section, and shows unvalidated skills separately.

This helps distinguish a simple skill list from skills demonstrated through actual work.

## 13. Database and security

### Stored analysis fields

The `analyses` table stores an ID, authenticated `user_id`, resume filename, overall ATS score, keyword match value, missing keywords, timestamp and the complete analysis JSON.

### Security flow

- Supabase generates the user access token after login.
- The Streamlit frontend attaches it as `Authorization: Bearer <token>`.
- FastAPI verifies the signature and audience of the token.
- The backend obtains the user ID from the token, not from frontend input.
- History read/delete operations are restricted by this verified user ID.
- The service-role key stays only on the backend and should never be exposed in public frontend code.

## 14. API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API information and endpoint list |
| GET | `/api/v1/health` | Checks whether NLP models are loaded |
| POST | `/api/v1/analyze-resume` | Analyzes resume and optional JD |
| GET | `/api/v1/history` | Gets signed-in user’s saved analyses |
| DELETE | `/api/v1/history/{analysis_id}` | Deletes one owned history item |
| POST | `/api/v1/generate-pdf` | Generates a report from current analysis data |
| GET | `/api/v1/history/{analysis_id}/pdf` | Generates a report from saved analysis |

## 15. Input and output

### Input

- Resume file: PDF or DOCX recommended, under 5 MB.
- Optional job-description text/file.
- Logged-in user session token.

### Output

- Overall ATS score out of 100.
- Five component scores.
- Score interpretation.
- Strengths and critical issues.
- Detailed issue cards with severity, explanation, fix and example.
- Matched and missing JD keywords.
- JD match percentage and semantic similarity.
- Validated/unvalidated skills.
- Saved history and downloadable PDF report.

## 16. Advantages

- Provides instant and consistent feedback.
- Combines exact keyword checking with semantic AI comparison.
- Gives practical fixes instead of only a score.
- Helps users tailor resumes for a specific JD.
- Uses authentication so each user sees only their own history.
- Supports report export for later review.

## 17. Future enhancements

1. Add OCR for scanned/image-based resumes.
2. Support more file types, including legacy DOC after safe conversion.
3. Add multilingual resume analysis.
4. Add role-specific scoring templates, for example Data Analyst, Web Developer and HR.
5. Allow side-by-side comparison of multiple resume versions.
6. Add resume rewriting suggestions with user approval.
7. Add analytics charts for score improvement over time.
8. Add unit/integration tests and containerized deployment.
9. Add rate limiting and async job processing for production scale.

## 18. Conclusion

AI Resume ATS Analyzer demonstrates how web development, cloud authentication, large language models, NLP and semantic similarity can be combined to solve a real job-search problem. It automates resume analysis while keeping the results understandable through score breakdowns and actionable feedback. The project is useful as a student-focused career-support tool and can be extended into a larger recruitment-assistance platform.

---

# Part B — Presentation Plan and What to Speak

## Suggested presentation duration

**9–12 minutes total**, followed by demo and questions.

| Speaker | Suggested time | Sections |
|---|---:|---|
| Ankita | 3–4 minutes | Slides 1–4 |
| Prachi | 3–4 minutes | Slides 5–7 |
| Suchitra | 3–4 minutes | Slides 8–12 |

## Slide 1 — Title slide

**Put on slide**

```text
AI Resume ATS Analyzer
An Intelligent Resume Screening and Job Matching System

Presented by:
Ankita | Prachi | Suchitra
Department / College / Guide Name / Academic Year
```

**Ankita will say**

> Good morning/afternoon respected faculty members and everyone present. We are Ankita, Prachi and Suchitra. Our minor project is **AI Resume ATS Analyzer**. It is an intelligent web application that analyzes a user’s resume, optionally compares it with a job description, and gives an ATS-oriented score with detailed suggestions for improvement.

## Slide 2 — Problem statement

**Put on slide**

- Many resumes are rejected before human review.
- Students do not know ATS-friendly formatting or missing keywords.
- Manual resume review is slow and inconsistent.
- A personalized, automatic feedback system is needed.

**Ankita will say**

> Today, many companies use Applicant Tracking Systems to filter resumes. A candidate may have good skills but can still be rejected because the resume does not contain relevant keywords, has weak formatting, or does not clearly show project evidence. Manual checking is time-consuming. Therefore, we developed a system that gives users quick, structured and personalized ATS feedback.

## Slide 3 — Objectives and features

**Put on slide**

- Upload PDF/DOCX resume
- Optional JD comparison
- ATS score out of 100
- Five score components
- Missing keyword and skill-gap analysis
- Skill validation from project/experience evidence
- User login, history and PDF report

**Ankita will say**

> Our objectives were to extract resume content automatically, calculate a meaningful ATS score, compare the resume with a job description, and provide actionable feedback. The application also validates whether skills listed by the candidate are actually supported in their project or experience descriptions. For convenience, users can sign in, save past analyses and download a PDF report.

## Slide 4 — Technologies used

**Put on slide**

| Frontend | Backend | AI/NLP | Data/Auth |
|---|---|---|---|
| Streamlit + CSS | FastAPI + Python | Groq Llama, spaCy, MiniLM, RapidFuzz | Supabase |

**Ankita will say**

> We used Python throughout the project. Streamlit is used for the frontend because it supports fast interactive dashboards. FastAPI provides backend REST APIs. Groq with Llama 3.3 extracts structured details from unstructured resume text. spaCy, Sentence Transformers and RapidFuzz are used for NLP, semantic similarity and keyword matching. Supabase manages authentication and stores analysis history.

**Transition:** “Now Prachi will explain the architecture and how the analysis happens inside the system.”

## Slide 5 — System architecture

**Put on slide**

Use this compact diagram:

```text
User → Streamlit UI → FastAPI Backend → AI/NLP Services → Results Dashboard
                         │       │             │
                         │       │             └─ Groq: resume/JD JSON extraction
                         │       └─ spaCy + MiniLM + RapidFuzz: matching/scoring
                         └─ Supabase: authentication + history
```

**Prachi will say**

> This is our system architecture. The user interacts with the Streamlit interface, where they sign in and upload the resume. The frontend sends the file and the authenticated user token to the FastAPI backend. The backend first verifies the token and validates the file. It then extracts resume text and passes it through the AI and NLP pipeline. The final result returns to the dashboard, and a copy is saved in Supabase history for that user.

## Slide 6 — Workflow

**Put on slide**

```text
Login → Upload Resume + JD → Validate File → Extract Text
→ Groq Structured Parsing → NLP/JD Matching → ATS Scoring
→ Feedback Generation → Save History → Display / PDF Download
```

**Prachi will say**

> First, the user logs in and uploads a resume. We validate the file size, type and basic file signature. PDF text is extracted using pdfplumber with PyPDF2 as fallback, and DOCX text is extracted using python-docx. Groq converts the plain text into structured data such as skills, experience, education, projects, keywords and action verbs. If a job description is provided, it is also parsed. After that, our NLP modules perform matching and the system generates scores and feedback.

## Slide 7 — AI/NLP pipeline

**Put on slide**

- Groq: converts unstructured text to structured JSON
- MiniLM: semantic similarity using embeddings and cosine similarity
- RapidFuzz: fuzzy keyword matching
- spaCy: noun phrases/entities for skill-gap candidates
- Exact + semantic comparison: skill evidence validation

**Prachi will say**

> Our project does not rely on only exact keyword matching. Groq first structures the resume. Sentence Transformer MiniLM converts text into embeddings, which let us measure semantic similarity between the resume and job description. RapidFuzz handles similar keyword spellings and aliases, for example ReactJS and React. spaCy extracts relevant phrases from the JD. Finally, the system checks whether each listed skill appears in a project or experience description, either directly or semantically.

**Transition:** “Now Suchitra will explain the scoring, results, database and future scope.”

## Slide 8 — ATS scoring model

**Put on slide**

| Component | Weight/maximum |
|---|---:|
| Formatting | 20 |
| Keywords | 25 |
| Content quality | 25 |
| Skill validation | 15 |
| ATS compatibility | 15 |

```text
Final ATS score = weighted component score + bonuses − penalties
```

**Suchitra will say**

> The system calculates five main components. Formatting checks sections and bullet points. Keywords checks relevant terms and JD overlap. Content quality checks action verbs and measurable achievements. Skill validation checks whether listed skills have evidence. ATS compatibility checks readable formatting and some privacy or special-character issues. These are combined into a final score out of 100, with certain bonuses and penalties.

## Slide 9 — JD matching and feedback

**Put on slide**

- Matched keywords
- Missing keywords
- Semantic similarity
- JD match percentage
- Potential skill gaps
- Detailed high/medium/low priority fixes

**Suchitra will say**

> When the user adds a job description, the system finds matched keywords and missing keywords. It also calculates semantic similarity, so it can compare meaning in addition to exact words. The JD match percentage uses 60 percent keyword overlap and 40 percent semantic similarity. The output then shows strengths, critical issues, and detailed fixes with a severity level, explanation, action items and an example improvement.

## Slide 10 — Authentication, database and security

**Put on slide**

```text
Supabase Login → JWT Token → FastAPI Token Verification
→ User-specific History in analyses table
```

- Backend derives user ID from verified token
- History is user-specific
- Service-role key remains server-side

**Suchitra will say**

> For authentication and storage, we use Supabase. After login, Supabase provides a JWT access token. The frontend sends this token to FastAPI, and the backend verifies it before allowing analysis-history operations. The user ID is read from the verified token, so users cannot simply send another user ID to access somebody else’s history. The complete result is stored in the analyses table and can later be used to generate a PDF report.

## Slide 11 — Output and demo

**Put on slide**

- Upload resume
- Add sample JD
- Click Analyze
- Show overall score and five components
- Show matched/missing keywords and feedback
- Show history/PDF export

**Suchitra will say**

> In the demo, we will upload a sample resume and add a job description. The application returns the overall ATS score, component-wise score breakdown, validated and unvalidated skills, matched and missing keywords, and improvement suggestions. After analysis, the record appears in the user history and can be downloaded as a PDF report.

## Slide 12 — Conclusion and future scope

**Put on slide**

- Combines web development, AI, NLP and cloud database
- Gives understandable, actionable resume feedback
- Can be expanded with OCR, multilingual support and role-specific templates

**Suchitra will say**

> To conclude, our project combines AI, NLP, full-stack web development and secure cloud storage to help job seekers improve their resumes. It gives more useful output than a simple score because it explains what to improve. In future, we can add OCR for scanned resumes, multilingual support, role-specific scoring templates, score-trend analytics and automatic resume rewrite suggestions. Thank you. We are ready for questions.

---

# Part C — Demo script

## Before presenting

1. Start the backend: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
2. Start frontend: `streamlit run frontend/streamlit_app.py`
3. Keep one small selectable-text PDF or DOCX resume ready.
4. Keep a short JD ready, for example for a Python/Web Developer.
5. Sign in before the presentation so login does not consume demo time.
6. Confirm the Groq key and Supabase configuration work before presenting.

## During demo: speak this

> We are now demonstrating the working application. After login, we open the ATS Scorer page. Here we upload a resume and paste the job description. When we click Analyze Resume, the backend validates and extracts the document text. The AI converts it into structured information, then our scoring and matching modules calculate the result. On the dashboard, we can see the score, component-wise breakdown, skills validation, JD match, missing keywords and detailed action items. Finally, the user can save the analysis in history and download the report as a PDF.

---

# Part D — Viva questions with short answers

| Question | Answer |
|---|---|
| What is ATS? | ATS means Applicant Tracking System. It is software used by recruiters to collect, search, filter and rank job applications. |
| Is your score the same as every company ATS score? | No. It is an educational heuristic based on common ATS-friendly signals; every company may use different rules. |
| Why did you use FastAPI? | It is fast, Python-friendly, provides automatic API docs, Pydantic validation and works well for AI service APIs. |
| Why did you use Streamlit? | It lets us build an interactive Python dashboard quickly, including file upload, forms, metrics and charts/components. |
| What is the role of Groq? | Groq provides Llama model inference. We use it to convert unstructured resume and JD text into structured JSON fields. |
| What are embeddings? | Embeddings are numerical vectors representing text meaning. Similar meanings produce vectors that are closer together. |
| What is cosine similarity? | It measures how similar two vectors point in the same direction. Here it helps compare resume text and JD text semantically. |
| Why use RapidFuzz? | It matches near-equivalent terms and spelling/format variations, such as ReactJS and React. |
| How are skills validated? | We look for direct mentions in projects/experience; otherwise we use semantic similarity with a threshold of 0.6. |
| How is user data secured? | Supabase creates JWT tokens. FastAPI verifies them and derives the user ID from the token before history operations. |
| What happens for scanned PDFs? | Currently text extraction fails for image-only PDFs because OCR is not included. Adding OCR is a future enhancement. |
| What is the maximum file size? | 5 MB. |
| Why is the JD optional? | Users can get a general ATS score without a JD; adding a JD provides tailored keyword and relevance analysis. |
| What is stored in the database? | Filename, user ID, score, keyword information, timestamp and complete analysis result JSON. |
| What is a limitation of LLM use? | It can make extraction mistakes and requires external API access, so outputs should be reviewed and privacy must be considered. |

---

# Part E — Submission checklist

- [ ] Add college name, department, guide name, academic year and team roll numbers on Slide 1.
- [ ] Add screenshots of the home page, scorer upload page, result dashboard and history page to your PPT/report.
- [ ] Include the architecture and workflow diagrams above.
- [ ] Add one sample input and its output screenshot.
- [ ] Practice the speaker handoff between Ankita, Prachi and Suchitra.
- [ ] Do not claim that the app is fully offline or that it exactly replicates a company ATS.
- [ ] Do not show `.env`, API keys, Supabase service-role key or `secrets.toml` in screenshots/presentation.
