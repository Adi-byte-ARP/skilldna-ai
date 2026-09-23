# SkillDNA AI

SkillDNA AI is an evidence-based career skill assessment platform that evaluates a user's skills using multiple sources instead of trusting a single resume claim. The system combines resume parsing, GitHub activity, LinkedIn profile data, and certificate evidence to generate a composite SkillDNA score.

[![CI](https://github.com/Adi-byte-ARP/skilldna-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/Adi-byte-ARP/skilldna-ai/actions/workflows/ci.yml)

[Open the live frontend](https://adi-byte-arp.github.io/skilldna-ai/)

Project Synopsis 22UIS717P — Basaveshwar Engineering College Bagalkote, Department of Information Science & Engineering.

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
uvicorn app.main:app --reload --port 8000
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
- Backend API: http://localhost:8000
- Docs: http://localhost:8000/docs

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
- http://localhost:5173

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
