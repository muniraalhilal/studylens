# StudyLens

**A little focus. A lot of progress.

**[Live app](https://studylens-3nuw.onrender.com) · [API docs](https://studylens-3nuw.onrender.com/docs) · [CI checks](https://github.com/muniraalhilal/studylens/actions)**

Free hosting can take 50 seconds or longer to wake after inactivity. Enter without registration to explore an isolated guest workspace.**

A bilingual study workspace with a Python/FastAPI backend: turn lecture files into extractive summaries, vocabulary practice quizzes, flashcards, and source-backed answers. Track your practice in a private account. Runs locally from VS Code without subscriptions, API keys, a frontend build tool, or an AI model download.

> العربية: مشروع متكامل يعمل محليًا، بواجهة عربية وإنجليزية ومظهر فاتح وداكن. [دليل التشغيل العربي](docs/README.ar.md).

![StudyLens overview](docs/screenshots/overview-en.png)

## No-signup demo and sharing

Choose **Try the demo — no sign-up** on the entry page. A real backend session creates an independent 24-hour workspace and loads both sample lectures. Each visitor has separate files and progress; no shared password is used. Personal accounts remain optional locally.

See [temporary HTTPS sharing](docs/SHARING.md) and [backend validation: 29 automated cases plus 21 live HTTPS checks](docs/BACKEND-VALIDATION.md).

## What works

- Account registration, login, logout, expiring database sessions and scrypt password hashing.
- User-isolated document library; upload, search, study, and delete materials.
- Text-based PDF, PowerPoint `.pptx`, UTF-8 `.txt` and `.md` processing with page/slide references.
- Offline sentence-ranking summaries and cloze flashcards.
- Multiple-choice cloze quizzes with server-side scoring, answer explanations and attempt history.
- Document questions answered with ranked, cited excerpts; explicit no-match state.
- Persistent review events and aggregate study progress.
- Full Arabic/English interface, RTL/LTR layout, persistent dark/light appearance, responsive mobile layout.
- SQLite by default; PostgreSQL configuration provided through SQLAlchemy and Docker Compose.
- OpenAPI/Swagger documentation, automated tests and GitHub Actions workflow.

## Stable CV deployment

Cloud deployment preparation is included for the same FastAPI backend on Render with persistent Neon PostgreSQL. See [deployment status and steps](docs/DEPLOYMENT.md). Deployed on Render with Neon PostgreSQL. GitHub CI passed **36 tests on SQLite and 36 on PostgreSQL**. The hosted service passed **21 HTTPS workflow checks** on 2026-09-29.

## Quick start in VS Code

Requires **Python 3.11+**. Python 3.12 was used for verification. Dependencies need internet access once; daily use is offline. No Node.js required.

1. Open the **StudyLens** folder in VS Code (the folder containing this README).
2. Open **Terminal → New Terminal**.
3. Create and activate a virtual environment:

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

4. Open **http://127.0.0.1:8000**. Select **Try the demo — no sign-up**. Personal registration remains optional; no email is sent.
5. Select **Explore sample materials**. English networking notes and Arabic database notes are copied into your account. This button is safe to repeat.
6. Open a material and explore Summary → Flashcards → Practice quiz → Ask your document → Source text.

Stop the server with **Ctrl+C**. Restart with the same command; accounts, documents and progress persist in `data/studylens.db`.

### VS Code debugging

Install the recommended Python and Python Debugger extensions, select the `.venv` interpreter using **Python: Select Interpreter**, then choose **StudyLens · FastAPI** in Run and Debug and press F5. On Windows, select `.venv\Scripts\python.exe` if the default macOS/Linux path is not detected.

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Absolute SQLite URL under `data/` | Set to PostgreSQL to use a database server |
| `APP_ORIGIN` | `http://127.0.0.1:8000` | Exact browser origin allowed for mutations |
| `COOKIE_SECURE` | `false` | Set to `true` when serving through HTTPS |

Use the exact `127.0.0.1` URL above. If using `localhost`, another port or a hosted domain, change `APP_ORIGIN` to match and restart. Never commit `.env` or `data/`.

### PostgreSQL (optional, free)

Install Docker with Compose, then:

```bash
docker compose up -d db
```

Uncomment the PostgreSQL `DATABASE_URL` in `.env`, then restart FastAPI. Tables are initialized on startup. The Compose password is a local demo default; replace it before using any shared environment. Switching database URLs selects a separate database and does not migrate existing SQLite data. Stop the database with `docker compose stop db`; its named volume preserves data. PostgreSQL is exercised by CI and the hosted service uses Neon PostgreSQL.

## How the free study engine works

The default engine is **offline and extractive**, not a generative language model. This is deliberately visible in the UI.

1. Extract selectable text, retaining page or slide numbers.
2. Split into overlapping, page-local text chunks.
3. Rank sentences by normalized word frequency for a source-faithful summary.
4. Mask key terms to generate recall cards and four-option cloze questions.
5. Rank chunks by query-term frequency and inverse document frequency for question answering.
6. Return up to three original passages with page and chunk references, or no-match.

This implements a retrieval-grounded **fallback** for a RAG-style workflow. It does not implement embedding/vector search or a generative RAG model. Answers are source passages, not a claim that an LLM reasoned about the document. No network requests leave the app during study. See [architecture and extension points](docs/ARCHITECTURE.md).

### Honest limitations

- Scanned PDFs require OCR before upload; OCR and legacy `.ppt`/`.doc` formats are not included.
- Maximum 10 MB per file, 200 pages/slides and 500,000 extracted characters. PDF reading quality depends on its text layer, especially Arabic PDFs.
- Queries use lexical matching. Synonyms, cross-language retrieval and complex reasoning may not match. Ask in the language of the uploaded text.
- Study content stays in its original language when you switch the interface language.
- Questions test missing-word recall; distractors can be simple. Scores are not comprehensive subject assessments.
- Flashcard ratings count review events, not unique mastered cards or a spaced-repetition schedule.
- Uploads are now parsed in a disposable subprocess with a 15-second timeout and Unix CPU limit, plus a Linux address-space limit. This is not a full OS sandbox. This local app does not yet have job queues, antivirus scanning, OCR workers, password reset, email verification or production-scale rate limiting.
- Authentication throttling is in-memory per process. TLS, shared throttling, backups, resource isolation, schema migrations and deployment hardening are needed before public multi-user hosting.

## Repository map

```text
backend/app/
  main.py               Application, middleware, static UI, health
  database.py           Environment loading and database sessions
  models.py             Users, sessions, documents, quizzes, reviews
  schemas.py            Validated request models
  security.py           Passwords and cookie authentication
  routers/
    auth.py             Registration and session lifecycle
    documents.py        Ownership, uploads, samples, retrieval, reviews
    quizzes.py          Quiz creation, atomic submission, progress
  services/study.py     File extraction and offline study engine
frontend/               Accessible, responsive HTML/CSS/JavaScript
samples/                Original English and Arabic lecture notes
tests/                 API and study workflow integration tests
docs/                  Architecture, demo walkthrough and Arabic setup
.vscode/                Run/debug configuration
.github/workflows/      CI test workflow
compose.yaml            Optional local PostgreSQL
```

## REST API

Interactive docs: **http://127.0.0.1:8000/docs**. OpenAPI: `/openapi.json`.

| Method | Endpoint | Behavior |
| --- | --- | --- |
| POST | `/api/auth/demo` | Start/resume a no-signup guest workspace with samples |
| GET | `/api/config` | Public demo configuration |
| POST | `/api/auth/register` | Register and set an HttpOnly session cookie |
| POST | `/api/auth/login` | Authenticate and start a session |
| POST | `/api/auth/logout` | Revoke current session |
| GET | `/api/auth/me` | Current user (no password information) |
| GET / POST | `/api/documents` | List own documents / multipart upload |
| POST | `/api/documents/samples` | Load bilingual sample materials |
| GET / DELETE | `/api/documents/{id}` | Study content / delete owned material |
| POST | `/api/documents/{id}/ask` | Query `{ "question": "TCP delivery" }` |
| POST | `/api/documents/{id}/reviews` | Save `{ "card_index": 0, "rating": "known" }` |
| POST | `/api/documents/{id}/quizzes` | Start quiz without revealing correct answers |
| POST | `/api/quizzes/{id}/submit` | Submit `{ "answers": [0, 1, 2, 3, 0] }` once |
| GET | `/api/progress` | Aggregate statistics and recent scored attempts |
| GET | `/api/health` | Service health and engine mode |

Quiz answer indices are zero-based. Supply exactly one valid option index for each returned question. File uploads use multipart field `file`. Errors use FastAPI's `detail` response; protected resources return 404 when owned by another account.

## Verification

```bash
python -m pytest -q
```

Tests cover authentication/session revocation, ownership isolation, the complete study workflow, scoring and repeat-submission protection, Arabic sample retrieval, PowerPoint extraction, malformed/oversized uploads, scanned PDF rejection, origin checks, throttling, and API/UI availability. Tests use a temporary isolated SQLite database.

Manual browser checks and screenshots are documented in [the demo guide](docs/DEMO.md).

## Portfolio presentation

- Use the real screenshots in `docs/screenshots/` in a GitHub README or portfolio page.
- Record the short flow in [DEMO.md](docs/DEMO.md), including Arabic RTL and dark mode.
- Suggested CV bullet: **Built StudyLens, a bilingual FastAPI study platform with authenticated document processing, source-cited retrieval, automated recall quizzes, and persistent progress tracking using SQLAlchemy.**
- Describe the default engine accurately as an offline extractive retrieval pipeline; don't claim an LLM, embeddings, OCR or a hosted service that is not included.
- Publish this folder as its own GitHub repository. The generated local database, secrets and virtual environment are excluded. Source repository: https://github.com/muniraalhilal/studylens. The sharing helper supports a temporary public preview.

## Technical references

[FastAPI uploads](https://fastapi.tiangolo.com/tutorial/request-files/) · [SQLAlchemy session lifecycle](https://docs.sqlalchemy.org/en/20/orm/session_basics/)

## License

MIT — see [LICENSE](LICENSE).
