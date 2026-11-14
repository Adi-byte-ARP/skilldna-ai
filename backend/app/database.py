"""
Database setup.

Uses SQLite for local development (zero config). Swap DATABASE_URL to a
Postgres/Supabase connection string for production — SQLAlchemy handles
both with no code changes elsewhere.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./skilldna.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_columns() -> None:
    """Add columns that were introduced after a database was first created.

    create_all() only creates missing tables, so an existing SQLite file needs these
    ALTER statements. Other databases (Postgres, Supabase) should get the same change from
    a proper migration tool.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return
    from app.services.account_rules import canonical_email
    with engine.begin() as conn:
        user_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)")}
        if "email_canonical" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN email_canonical VARCHAR")
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_users_email_canonical ON users (email_canonical)")
            for user_id, email in conn.exec_driver_sql("SELECT id, email FROM users").fetchall():
                conn.exec_driver_sql("UPDATE users SET email_canonical = ? WHERE id = ?",
                                     (canonical_email(email), user_id))
        sub_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(submissions)")}
        if "detected_name" not in sub_cols:
            conn.exec_driver_sql("ALTER TABLE submissions ADD COLUMN detected_name VARCHAR")
        for table, column, ddl in [
            ("users", "target_role", "VARCHAR"),
            ("users", "assistant_context", "BOOLEAN DEFAULT 1"),
            ("mock_sessions", "integrity_points", "FLOAT DEFAULT 0"),
            ("mock_sessions", "integrity_flags", "JSON"),
            ("mock_sessions", "end_reason", "VARCHAR"),
            ("interview_sessions", "integrity_points", "FLOAT DEFAULT 0"),
            ("interview_sessions", "integrity_flags", "JSON"),
            ("interview_sessions", "end_reason", "VARCHAR"),
        ]:
            existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            if existing and column not in existing:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        if "content_hash" not in sub_cols:
            conn.exec_driver_sql("ALTER TABLE submissions ADD COLUMN content_hash VARCHAR")
            conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_submissions_content_hash ON submissions (content_hash)")
