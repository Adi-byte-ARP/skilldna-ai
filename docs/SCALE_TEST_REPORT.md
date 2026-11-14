# SkillDNA AI: Full Scale Test Report

## Environment

- Sandbox: 1 CPU core, Linux, Python 3.12, SQLite database, single uvicorn worker.
- Latency numbers below describe this small machine, not production. Relative results (before vs after, errors vs none) are the useful part.

## What was run

| Stage | What | Result |
|---|---|---|
| 1 | Backend pytest suite | 38 passed at the time of this test. Current suite: 66 passed (see the update below). |
| 1 | Frontend `vite build` | Passes |
| 1 | Frontend lint (oxlint) | 0 warnings, 0 errors |
| 2 | Live API walkthrough (14 checks) | 14/14 after fixes |
| 3 | Concurrency scale test (`backend/scripts/scale_test.py`) | 0 server errors after fixes |

## Bugs found and fixed

1. **Report reads returned HTTP 500 under concurrency (2 of 500 before the fix).**
   `GET /report` deleted and rewrote the user's score rows on every read. Overlapping reads
   for the same user raced: one deleted rows the other was refreshing, giving
   `Could not refresh instance`. Fix: the report is now computed in memory and never writes.
   Nothing read the stored rows, so nothing else changed. Regression test added.

2. **Any user could read or change any other user's data by changing the number in the URL.**
   Routes for `/report`, `/resume`, `/github`, `/ocr` and `/users` trusted the `user_id` in the path.
   A probe without a login token returned a full report (200). Fix: a shared `authorize_user`
   dependency now requires a login and checks that the token belongs to the same user (401 without
   a token, 403 for another user). Tests added.

3. **`GET /users/{id}` and `POST /users` leaked accounts.** `POST /users` returned an existing
   account's name and email to anyone who submitted the address. It now returns 410 Gone and
   points to `/auth/register`. No frontend screen called it.

4. **A hostile upload filename caused HTTP 500.** A name such as `../../evil.pdf` was used raw
   in the save path and crashed on a missing folder. Stored names are now a random id plus a
   sanitized copy of the name (`app/utils/files.py`). Tests added.

5. **`/health` was missing** after the earlier refactor, so container health checks would fail.
   Restored.

6. **The scale script itself had a bug:** it counted successful responses as errors (390 false
   failures). Fixed and re-run to 0.

## Measured numbers (after fixes, 1 CPU sandbox)

| Phase | Requests | Concurrency | p50 | p95 | p99 | Errors |
|---|---|---|---|---|---|---|
| Registration | 50 | 10 | 1.66 s | 2.08 s | 2.21 s | 0 |
| Resume upload | 50 | 10 | 3.50 s | 4.43 s | 4.88 s | 0 |
| Report reads | 500 | 50 | 1.85 s | 2.57 s | 3.23 s | 0 (was 2 before fix) |
| Mock session flows | 50 | 20 | 1.18 s | 2.68 s | 3.11 s | 0 |

Before the fix, the report phase produced 2 HTTP 500 responses out of 500 requests.

## Known limits of this test

- It ran on a single CPU, so requests queue behind one another. Throughput on a normal server
  will be higher.
- The GitHub analysis was not load-tested because it depends on the GitHub API rate limit.
- The browser mock-exam page was not exercised in a real browser (none is available in the
  sandbox). Its logic was reviewed and the API it calls was tested.
- Docker build was not run (no Docker in the sandbox).

## Improvement ideas, by priority

### Security (do before publishing)
1. Refuse to start in production with the default `SECRET_KEY`. Right now it only falls back silently.
2. Rate-limit `/auth/login` and `/auth/register` to slow password guessing.
3. Enforce upload size limits (for example 10 MB). Nothing caps the size today.
4. JWTs are stored in `localStorage`, which a successful XSS attack could read. Consider an
   httpOnly cookie with CSRF protection.
5. Delete uploaded resumes after parsing and keep only extracted skills. Resumes are personal
   data, and the upload folder currently grows forever.
6. Add account deletion and data export (relevant to India's DPDP Act 2023).

### Performance and scale
7. Move PDF and OCR parsing into a background worker (RQ, Celery, or FastAPI background tasks)
   and return `202 Accepted` with a status endpoint. Parsing is the slowest step (about 3.5 s
   for one resume here).
8. Cache the computed report and invalidate it on upload, instead of recomputing on every read.
9. Move from SQLite to PostgreSQL for concurrent writes. Until then, run a single worker.
10. Store uploads in object storage (S3 or similar) so several app instances can share them.
11. Password hashing takes about 134 ms per hash, deliberately. Keep it, but do it in a thread pool
    so it does not block other requests under load.

### Product and accuracy
12. The taxonomy is small. Missing skills that appear in real resumes include Next.js, HTML, CSS,
    PHP, Firebase, XGBoost, LangGraph and Prompt Engineering. Expand it, ideally from a
    recognized list such as ESCO.
13. GitHub counts only each repository's primary language, so backend work is invisible when a
    frontend repo is larger. Consider the per-repo language byte counts endpoint, mindful of the rate limit.
14. Calibrate the noisy-OR scoring against real examples. The combination rewards multiple sources
    strongly, so one generous source can dominate.
15. Mock interview scoring is keyword coverage. Add an LLM rubric with human review before using
    it for anything consequential.
16. The mock exam cannot detect a second person or device from the browser. Consider face-presence
    checks in the browser (for example MediaPipe), weighing the privacy cost.
17. Paginate the mock session history (currently capped at 50).

### Quality and operations
18. Add browser end-to-end tests (Playwright) for login, upload, report and the mock exam. This is
    the biggest gap in the current testing.
19. Add a CI job that builds both Docker images and runs the backend suite and scale script.
20. Replace `datetime.utcnow()` and class-based Pydantic `Config` (deprecation warnings in the test run).
21. Remove the legacy `POST /users` code now that it returns 410.
22. Add structured logging and request IDs so production errors can be traced.


## Update: later test runs

The backend suite now has 66 tests (added plan, daily challenge, reminders and progress tests).
Frontend: 22 unit tests (Vitest, jsdom). Browser: 7 end-to-end checks in `e2e/` (headless Chromium).
The numbers in the tables above are from the run they describe and are not updated.
