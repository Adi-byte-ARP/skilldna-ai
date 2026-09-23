from dotenv import load_dotenv
load_dotenv()  # must run before app.database / app.utils.security / app.services.* import,
                # since those read env vars (DATABASE_URL, SECRET_KEY, TESSERACT_CMD, etc.) at import time

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers import users, resume, github, ocr_uploads, report, auth

# create tables on startup (fine for SQLite/dev; use Alembic migrations
# once you move to Postgres for anything beyond local dev)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SkillDNA AI",
    description="AI-powered career assessment platform — consolidates resume, "
                 "GitHub, LinkedIn, and certificate data into one composite score.",
    version="0.1.0",
)

# Comma-separated list, e.g. CORS_ORIGINS=https://skilldna.vercel.app,http://localhost:5173
# Defaults to "*" so local dev works with zero config out of the box.
_cors_origins_env = os.getenv("CORS_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_origins_env.split(",")] if _cors_origins_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(resume.router)
app.include_router(github.router)
app.include_router(ocr_uploads.router)
app.include_router(report.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "SkillDNA AI backend"}
