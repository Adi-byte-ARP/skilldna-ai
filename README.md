# SkillDNA AI

SkillDNA AI is an evidence-based career skill assessment platform that evaluates a user's skills using multiple sources instead of trusting a single resume claim. The system combines resume parsing, GitHub activity, LinkedIn profile data, and certificate evidence to generate a composite SkillDNA score.

[![CI](https://github.com/Adi-byte-ARP/skilldna-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/Adi-byte-ARP/skilldna-ai/actions/workflows/ci.yml)

[Open the live frontend](https://adi-byte-arp.github.io/skilldna-ai/)

Project Synopsis 22UIS717P — Basaveshwar Engineering College Bagalkote, Department of Information Science & Engineering.

Live deployment refreshed on 2026-10-02.

## Overview

Most career tools rely on what a candidate writes on a resume. SkillDNA AI challenges that by verifying whether the claimed skills are actually supported by evidence from real sources.

The app analyzes:
- Resume PDF content
- GitHub public repositories and language usage
- LinkedIn profile exports/screenshots
- Certificates and course uploads

Then it produces:
- overall score out of 100
- skill-by-skill confidence scores
- strengths and gaps
- actionable roadmap suggestions
- visually represented evidence strands

## Why this project matters

This project helps students and early-career professionals understand the gap between:
- what they claim to know
- what they have actually demonstrated

It reduces false confidence and gives a clearer view of where skills are strong and where they need more evidence.

## Features

### Resume intelligence
- Extracts skills from uploaded PDF resumes
- Normalizes skill names and recognizes common technologies
- Builds a claim base for each user

### GitHub evidence analysis
- Checks public GitHub profiles and repositories
- Reads repository language usage and project activity
- Identifies practical technical competence from code artifacts

### LinkedIn and certificate validation
- Accepts LinkedIn exports or screenshots
- Supports PDF and image uploads for certificate evidence
- Uses OCR fallback when needed

### SkillDNA scoring engine
- Combines evidence from all sources
- Scores skills by confidence and proof strength
- Highlights verified skills vs. weakly supported claims
- Produces strengths, gaps, and role-fit recommendations

### Dashboard experience
- React landing page and app dashboard
- Evidence upload cards for every source
- Real-time score and report updates
- Visual DNA-style representation of claimed vs verified strengths

## Tech Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- PyMuPDF / PDFPlumber
- Tesseract OCR support
- JWT authentication

### Frontend
- React
- Vite
- GSAP
- Framer Motion
- Recharts

## Project Structure

```text
skilldna-ai-repo/
├── backend/
│   ├── app/
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routers/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   ├── scripts/
│   └── uploads/
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── .gitignore
└── .github/
```

## Getting Started

### 1) Clone the repository

```bash
git clone https://github.com/Adi-byte-ARP/skilldna-ai.git
cd skilldna-ai
```

### 2) Start the backend

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### 3) Start the frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

### 4) Open the app

Visit:
- Live frontend: https://adi-byte-arp.github.io/skilldna-ai/
- Frontend: http://localhost:5173
- Backend API: http://localhost:8001
- Docs: http://localhost:8001/docs

## Environment Setup

Create a backend environment file if needed:

```bash
cp backend/.env.example backend/.env
```

Important variables may include:
- `SECRET_KEY`
- `GITHUB_TOKEN`
- `DATABASE_URL`
- `TESSERACT_CMD` for Windows OCR install setup

## Deploying to Vercel and Render

The frontend is hosted on Vercel. The API runs on Render with a persistent disk for
the SQLite database and uploaded files; the local database and uploads are not
included in deployment.

1. Connect the GitHub repository to Render and use the root `render.yaml`
   Blueprint to create the API. It generates a production `SECRET_KEY`.
2. In Vercel, import the same repository and set the project root to `frontend`.
   Set the build environment variable `VITE_API_URL` to the Render service URL
   (for example, `https://skilldna-ai-api.onrender.com`), then deploy.
3. Set Render's `CORS_ORIGINS` environment variable to the Vercel production
   origin, then redeploy the API.

## OCR Setup

OCR is required for LinkedIn screenshots and image-based certificate uploads.

Check if Tesseract is already available:

```bash
tesseract --version
```

If it is not installed:

### Linux
```bash
sudo apt-get install tesseract-ocr
```

### macOS
```bash
brew install tesseract
```

### Windows
Install Tesseract from the official project, then set the path in `backend/.env`:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Running with Docker

This project also supports Docker-based local running:

```bash
docker compose up --build
```

Then open:
- http://localhost:5173/

This is useful for a consistent environment and for deployment-friendly setup.

## Verified Project Status

The project has been checked locally and is functioning in its current version-2 state:

- GitHub repo is connected and the current branch is `main`
- App frontend responds successfully on `http://localhost:5173`
- The dashboard loads correctly and renders the SkillDNA UI
- The project contains a working evidence-based assessment workflow

## Key Implementation Notes

- The app follows a noisy-OR evidence scoring style: a skill gains confidence when multiple independent sources agree.
- The dashboard is designed around the DNA metaphor: claims on one side and proof on the other.
- GitHub analysis reduces API overhead by relying on repository metadata instead of repeated expensive calls.
- Authentication is implemented with JWT-based login and protected routes.
- LinkedIn uploads count only the **Skills section**. A LinkedIn screenshot also shows a right-hand sidebar with other people's headlines; OCR of the whole screenshot had picked up other people's skills. The parser now (1) drops words in the sidebar column when the screenshot visibly has one (detected from sidebar phrases such as "Who your viewers also viewed"), and (2) matches skills only between a "Skills" heading and the next profile section heading. A screenshot or PDF with no Skills section is rejected with an explanatory message instead of being scored from the rest of the page. Certificates and resumes are unaffected. Tests: `backend/tests/test_linkedin_section.py`. LinkedIn also contributes weak communication evidence from the connection count on the profile card (1+ connections 0.30, 50+ 0.40, 100+ 0.50, 300+ 0.60, 500+ 0.70). A connection count measures networking reach, not communication skill, so it stays low and capped.

## Mock Test and Mock Interview

`/app/mock` (linked from the dashboard) runs a proctored mock test or mock interview for a target role.

- **Rules the server enforces:** one active session per user; a deadline fixed at start; each violation recorded; the third violation ends and scores the session. Answer keys and expected keywords are never sent before the session ends.
- **Rules the browser enforces:** fullscreen (leaving it blocks the screen until it is restored), tab and window focus changes, copy, cut, paste, right-click, and blocked shortcuts (Ctrl/Cmd + C, V, X, U, S, P, F12, DevTools) are all reported. The camera must be on, and turning it off is recorded.
- **Scoring:** tests score the share of correct answers, with a per-skill breakdown. Interviews use a keyword-coverage rubric plus answer length. It checks whether expected points were mentioned, not how well the answer was delivered.
- **Limits:** a browser cannot see a second device or a person in the room, and the camera feed is not analyzed for faces. Video is never uploaded. Only the event log and answers are stored.

API: `GET /mock/roles`, `POST /mock/sessions`, `GET /mock/sessions/{id}`, `POST /mock/sessions/{id}/events`, `POST /mock/sessions/{id}/answers`, `POST /mock/sessions/{id}/submit`. Tests: `backend/tests/test_mock.py`.

## Improve Plan and Daily Challenge

**Improve plan** (`/app/plan`, linked from the dashboard) builds a detailed roadmap for a target role. For every skill the role expects that the user has not shown (missing) or shows only weakly (below 60, weak), it gives:

- why it matters, three objectives, three weekly tasks you can tick off (progress is saved), a project, official resource links, an hour estimate and how you will know you are ready
- phases sized by study hours at about 20 hours a week, each with a week range, followed by a proof phase (one mock test, one mock interview, a daily streak)

Skills that appear on a resume only are shown as weak, not missing, because one source is not enough to confirm them.

**Daily challenge** (`/app/daily`) gives one question each day. Most days cover the user's skill gaps. Every third day explores a skill outside them. The question is the same for the whole day, the answer is revealed only after answering, and each day can be answered once. The page shows the streak, points and the last 30 days.

API: `GET /plan?role=`, `POST /plan/tasks/{task_key}`, `GET /daily/today?role=`, `POST /daily/answer`, `GET /daily/history`. Tests: `backend/tests/test_plan_daily.py`. Frontend tests: `frontend/src/test/`, run with `npm test`.

## Daily challenge: free text, progress and reminders

- **Question bank:** 85 multiple-choice and 17 free-text daily questions across 18 skills, each with an explanation shown after answering. Free-text answers are graded by keyword: a question states how many of its accepted keywords are needed.
- **Skill progress on the plan:** the first time you open the plan, each gap skill's score is recorded as its starting point. The plan then shows the score change, tasks ticked, and how many daily challenges on that skill you got right in the last 30 days. Ticking tasks does not change your score by itself. The score moves when new evidence is added (a certificate, a GitHub update, a LinkedIn screenshot, or a resume), and the plan says so.
- **Reminders:** off by default. The daily page shows a notice after 6 pm local time while today's question is open. Browser notifications need your permission. Email reminders need your opt-in. Send them with `backend/scripts/send_reminders.py`: it is a dry run unless you pass `--send`, and it needs `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` and `APP_URL`. Schedule it once a day with cron or Task Scheduler.

API: `GET /daily/status?local_hour=`, `GET /reminders/settings`, `PUT /reminders/settings`.

## Browser end-to-end checks

`e2e/` drives the real app in headless Chrome: register, dashboard, improve plan, daily challenge, and the proctored mock exam through to its result. See `e2e/README.md` for the three commands to run it.

## Motion (GSAP)

All animation uses GSAP, with ScrollTrigger for scroll-linked motion.

- **Landing page:** an aurora of soft colour fields drifts behind the page. A double helix on the right rotates continuously and drifts with scroll. A progress bar fills at the top, and the hero has a cursor glow on mouse devices. "How it works" sticks while its steps light up in order and the sequence line draws. The explainer text lights up word by word as you scroll.
- **App pages:** the dashboard, plan, daily challenge, exam screens and login use the same aurora and entrance motion. Plan progress bars glide, cards reveal once as they scroll in, and the score counts up.
- **Shared code:** `frontend/src/lib/motion.js` holds `useGsap` (scoped, cleaned up on unmount, respects reduced motion). The components are `AmbientBackground`, `HelixBackdrop`, `ScrollProgress`, `ScrubText`, `Appear` and `SequenceBackground`.
- **Reduced motion:** with `prefers-reduced-motion`, nothing is hidden or moved. The helix stays still and the steps don't pin or scrub.
- **Live exam:** the timed exam screen itself is not animated, so nothing distracts from the clock.

Browser checks for the motion are in `e2e/motion.mjs` (13 checks, including reduced motion and a phone layout).

## Accounts, identity checks and practice history

- **Sign-up:** a real Gmail address (`name@gmail.com`, 6 to 30 characters, letters, numbers and single dots). Gmail ignores dots, so `a.dith@gmail.com` and `adith@gmail.com` are the same mailbox and cannot both register. The password needs 8+ characters with an uppercase letter, a lowercase letter, a number and a symbol, and must not contain your Gmail name or be a common password. The form shows each rule as you type and needs the confirm field to match. Registration needs a first and last name, because documents are checked against it.
- **Identity on uploads:** the name on each resume, LinkedIn upload and certificate must match the account name. The first name must match, and so must the surname when both have one. Initials and accents are ignored. A document that does not match, or has no readable name, is kept but not counted toward the score, and the upload shows why.
- **Certificates:** every file in a batch is scanned. A bad file gets its own error and the rest still run. The card lists each file with its own result.
- **Practice cards:** the dashboard shows Improve plan, Daily challenge and Mock test & interview as cards, each with a headline stat and its latest history. Each feature page has a history panel. The plan records one snapshot per role per day.
- **Existing databases:** on startup, SQLite databases gain the `email_canonical` and `detected_name` columns automatically. Other databases need a proper migration. Logins now require a Gmail address, so accounts registered with another domain cannot sign in.

## Architecture and design system

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the layers, design tokens, components, motion rules, and the decisions behind them.

## Future Improvements

Planned enhancements include:
- stronger production deployment configuration
- expanded role-based recommendations
- more advanced skill taxonomy coverage
- improved scoring for edge-case evidence sources
- LLM-powered recommendation generation

## License and Project Context

This project is developed as part of:
- 22UIS717P
- Basaveshwar Engineering College Bagalkote
- Department of Information Science & Engineering

## Repository

GitHub:
https://github.com/Adi-byte-ARP/skilldna-ai

## Contribution

Contributions, issue reports, and suggestions are welcome. See `CONTRIBUTING.md` for project contribution guidelines.
