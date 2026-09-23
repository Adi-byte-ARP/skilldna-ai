# SkillDNA AI

An AI-powered career assessment platform. Cross-checks your resume,
GitHub, LinkedIn, and certificates against each other and gives every
skill an evidence-backed confidence score — instead of just taking your
resume's word for it.

[![CI](https://github.com/Adi-byte-ARP/skilldna-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/Adi-byte-ARP/skilldna-ai/actions/workflows/ci.yml)

Project Synopsis 22UIS717P — Basaveshwar Engineering College Bagalkote,
Dept. of Information Science & Engineering.

## What's here

- **`backend/`** — FastAPI + SQLAlchemy. Resume/PDF parsing, GitHub API
  analysis, OCR (Tesseract) for LinkedIn/certificate screenshots, and the
  scoring engine that combines all sources into one composite score.
- **`frontend/`** — React + Vite + Tailwind v4 + GSAP. A landing page with
  scroll-driven GSAP animations and a working dashboard (upload sources →
  live SkillDNA report with charts).

## Run it (two terminals)

**Terminal 1 — backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Needs the Tesseract OCR engine installed system-wide for the LinkedIn/certificate
upload features to work (everything else, including resumes, works without it).
See "OCR setup" below.

**Terminal 2 — frontend**
```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** — that's the landing page. Click
through to `/app` to create a profile, upload sources, and watch your
SkillDNA score build in real time.

The frontend talks to the backend at `http://localhost:8000` by default
(see `frontend/.env` — `VITE_API_URL`). Change it there if you run the
backend somewhere else.

## Run it with Docker (recommended if you're sharing/deploying this)

The manual setup above needs Tesseract installed separately, and on
Windows that means a manual PATH fix (see "OCR setup" below). Docker
sidesteps all of that — Tesseract is baked into the backend image, so
`docker compose up` gives you a fully working app, OCR included, on any
machine that has Docker, no matter what OS it's running.

```bash
docker compose up --build
```

Then open **http://localhost:5173**. First build takes a few minutes
(installing dependencies inside the images); after that it's fast.

This is also the easiest path to actually deploying it somewhere (Render,
Railway, Fly.io, or any host that runs Docker images) — push the same
images there and Tesseract comes along for free.

Notes:
- Data persists in named Docker volumes (`skilldna-data`, `skilldna-uploads`), not on your host filesystem — `docker compose down -v` wipes it, plain `docker compose down` keeps it.
- Set `SECRET_KEY` and `GITHUB_TOKEN` as real env vars (or a `.env` file next to `docker-compose.yml`) before sharing this with anyone else — see `backend/.env.example`.
- I wasn't able to actually run `docker build` in the environment I built this in (no Docker available there) — I verified the pieces I could (a clean `pip install -r requirements.txt` succeeds with no build errors, and every package imports cleanly), but the Docker build itself is untested. Worth a quick `docker compose up --build` sanity check on your end before you rely on it.

## Fixed since the last round (real bugs, found by testing)

- **GitHub false "not found" on pasted URLs** — usernames are now normalized:
  `github.com/user`, `https://github.com/user/`, `@user` all work, not just
  bare usernames.
- **GitHub rate-limit exhaustion** — the analyzer used to make 1 API call
  *per repo* just for language breakdown, burning through the 60/hr
  unauthenticated quota almost immediately on shared networks. It now uses
  each repo's primary language (included free in the repo list), cutting
  every analysis down to 2 API calls total. Set `GITHUB_TOKEN` in env to
  raise the limit further to 5,000/hr.
- **LinkedIn OCR requires Tesseract, which isn't always installed** —
  LinkedIn upload now also accepts a PDF (LinkedIn's own "Save to PDF"
  profile export), which needs zero OCR. If Tesseract truly isn't
  installed and someone uploads an image anyway, the error message now
  gives the exact install command instead of a raw stack trace.
- **Certificates only accepted single images** — now accepts PDFs (with
  automatic OCR fallback for scanned/image-only PDFs) and multiple files
  in one upload.
- **False-positive skill extraction** — short aliases like "js" were
  matching inside compound words ("React.js" → phantom "javascript"), and
  "R"/"Go"/"C" were matching inside ordinary text ("R&D" → phantom "R"
  language). These now require clear list-context (comma/bullet/colon
  delimited) before counting as a match.
- **Generic recommendations** — rewritten to name real skills from your
  actual data with specific next actions per skill category, plus an
  overall tier label and a role-fit suggestion based on your strongest
  verified category.

## The design

The signature visual is a DNA double-helix: the left strand is what you
*claim* (resume, LinkedIn), the right strand is *verified evidence*
(GitHub, certificates). A rung between them lights up teal when a skill
is confirmed by more than one source — that's not decoration, it's a
literal picture of how the scoring engine's noisy-OR combination works
(see `backend/app/services/scoring_engine.py`).

## Tested end-to-end

- `backend/tests/test_pipeline.py` — generates a sample resume PDF, runs
  it through parsing + scoring, verifies sane output (3/3 passing)
- Live HTTP smoke test — created a user, uploaded a real PDF, pulled a
  working composite report via curl, confirmed correct extraction and
  scoring
- `npm run build` — production frontend bundle builds clean, no errors

## OCR setup

Tesseract is a system binary, not a Python package, so `pip install` alone
doesn't get you OCR. Check if you already have it:

```bash
tesseract --version
```

If that fails, either run the helper script:

```bash
bash backend/scripts/setup_ocr.sh
```

or install it yourself:

- **Linux**: `sudo apt-get install tesseract-ocr`
- **Mac**: `brew install tesseract`
- **Windows**: download the installer from
  [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki), then
  set `TESSERACT_CMD` in `backend/.env` to the installed path (Tesseract is
  usually *not* added to PATH automatically on Windows):
  ```
  TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
  ```

Copy `backend/.env.example` to `backend/.env` to set this (or `SECRET_KEY`,
`GITHUB_TOKEN`, `DATABASE_URL`) — it's loaded automatically on startup.

Without Tesseract, resume upload (PDF) still works fully; only LinkedIn
screenshots and image-based certificates need it (PDF certificates work
either way, via direct text extraction).

## Fixed: GitHub analysis crash

Every GitHub analysis was failing with `Unexpected error: 'repo_count'`.
Root cause: `backend/app/routers/github.py` referenced
`github_data['repo_count']`, a key that `fetch_github_profile()` never
actually returns (it returns `{"profile": ..., "repos": ...}`) — so the
request crashed with a `KeyError` right after skills were extracted but
before they were saved, on every single call regardless of username.
Fixed to use `len(github_data['repos'])`. Verified end-to-end with a
mocked GitHub response (real GitHub API is rate-limited to 60 req/hr
unauthenticated, which is easy to exhaust while testing — see the
`GITHUB_TOKEN` note above) — skills now extract, save, and flow into the
score correctly.

## Auth

Real accounts now back the profile flow: `POST /auth/register` and
`POST /auth/login` return a JWT (`PyJWT`, `HS256`), and passwords are hashed
with PBKDF2-SHA256 (stdlib `hashlib`, no C-extension build step to fight
with). `GET /auth/me` verifies a bearer token and returns the current user —
the frontend calls this on load instead of trusting a cached user object, so
a stale/tampered localStorage entry can't fake a session.

Set `SECRET_KEY` in `backend/.env` for anything beyond local dev — the
default is a dev-only placeholder and is **not** safe to deploy with.

The old `POST /users` (no password) endpoint still exists for backward
compatibility but the frontend no longer calls it — `/login` is the only
way into `/app` now, which is a real `ProtectedRoute` that checks the
token before rendering the dashboard.

## What's next
- Deploy: swap `DATABASE_URL` to Postgres/Supabase, host frontend
  (Vercel/Netlify) and backend (Render/Railway/Fly)
- Wire up the still-existing `/resume`, `/github`, `/ocr` routes to trust
  `get_current_user`'s `user_id` instead of the URL path parameter, now that
  auth exists
- LLM-generated recommendations (the seam is
  `scoring_engine._generate_recommendations` — currently rule-based)
- Expand the skills taxonomy in `backend/app/utils/skills_taxonomy.py`
