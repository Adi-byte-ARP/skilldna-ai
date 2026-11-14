"""Concurrency smoke / scale test for a running SkillDNA backend.

Usage (server must already be running):
    python backend/scripts/scale_test.py --base http://127.0.0.1:8000 --pdf path/to/resume.pdf

Measures latency percentiles and status-code counts for four phases:
registration, resume upload, report reads, and mock-session writes.
Exits non-zero if any request returned a 5xx, so it can run in CI.
"""
import argparse
import collections
import concurrent.futures as cf
import io
import statistics
import sys
import time
import uuid

import httpx


def make_pdf() -> bytes:
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 800, "Load Test Resume - Skills: Python, React, SQL, Docker, Git")
    c.save()
    return buf.getvalue()


def timed(fn):
    t = time.perf_counter()
    try:
        r = fn()
        code = "ok" if r.status_code < 400 else str(r.status_code)
        return code, time.perf_counter() - t
    except Exception as e:  # network-level failures count as errors
        return type(e).__name__, time.perf_counter() - t


def report(name, rows, wall):
    """Print one phase's summary and return how many 5xx / network errors it had."""
    codes = collections.Counter(c for c, _ in rows)
    lat = sorted(l for _, l in rows)
    pct = lambda q: lat[min(len(lat) - 1, int(q * len(lat)))] * 1000
    print(f"\n[{name}] n={len(rows)} wall={wall:.1f}s rps={len(rows) / wall:.1f}")
    print(f"  p50={pct(.5):.0f}ms p95={pct(.95):.0f}ms p99={pct(.99):.0f}ms max={lat[-1] * 1000:.0f}ms")
    print("  status:", dict(codes))
    # network-level exceptions (e.g. "ReadTimeout") and 5xx responses count as errors;
    # "ok" (< 400) and 4xx are expected outcomes and do not.
    return sum(v for k, v in codes.items() if k != "ok" and (not k.isdigit() or int(k) >= 500))


def register_user(base, i):
    with httpx.Client(base_url=base, timeout=60) as c:
        r = c.post("/auth/register", json={
            "name": f"Load {i}", "email": f"load-{uuid.uuid4().hex[:8]}@test.dev", "password": "TestPass123"})
        return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--pdf", default=None, help="resume PDF to upload (default: generated)")
    ap.add_argument("--users", type=int, default=50)
    ap.add_argument("--reads", type=int, default=500)
    args = ap.parse_args()
    pdf = open(args.pdf, "rb").read() if args.pdf else make_pdf()
    base = args.base
    failures = 0

    # 1. registration (timed)
    t0 = time.time()
    with cf.ThreadPoolExecutor(10) as ex:
        rows = list(ex.map(lambda i: timed(lambda: register_user(base, i)), range(args.users)))
    failures += report("register", rows, time.time() - t0)
    # Create the users whose tokens the later phases use (setup, not timed).
    with cf.ThreadPoolExecutor(10) as ex:
        users = list(ex.map(lambda i: register_user(base, 10_000 + i).json(), range(args.users)))

    # 2. resume upload
    def upload(u):
        with httpx.Client(base_url=base, timeout=120) as c:
            return c.post(f"/resume/upload/{u['user']['id']}",
                          headers={"Authorization": f"Bearer {u['token']}"},
                          files={"file": ("cv.pdf", pdf, "application/pdf")})
    t0 = time.time()
    with cf.ThreadPoolExecutor(10) as ex:
        res = list(ex.map(lambda u: timed(lambda: upload(u)), users))
    failures += report("resume upload", res, time.time() - t0)

    # 3. report reads
    def read(u):
        with httpx.Client(base_url=base, timeout=60) as c:
            return c.get(f"/report/{u['user']['id']}", headers={"Authorization": f"Bearer {u['token']}"})
    jobs = [users[i % len(users)] for i in range(args.reads)]
    t0 = time.time()
    with cf.ThreadPoolExecutor(50) as ex:
        res = list(ex.map(lambda u: timed(lambda: read(u)), jobs))
    failures += report("report reads", res, time.time() - t0)

    # 4. mock sessions (write-heavy)
    def mock_flow(u):
        with httpx.Client(base_url=base, timeout=60) as c:
            h = {"Authorization": f"Bearer {u['token']}"}
            s = c.post("/mock/sessions", headers=h, json={"kind": "test", "role": "Backend Engineer"})
            if s.status_code != 200:
                return s
            sid, qid = s.json()["id"], s.json()["questions"][0]["id"]
            c.post(f"/mock/sessions/{sid}/answers", headers=h, json={"question_id": qid, "answer": 0})
            last = None
            for ev in ["tab_hidden", "window_blur", "copy"]:
                last = c.post(f"/mock/sessions/{sid}/events", headers=h, json={"type": ev})
            return last
    t0 = time.time()
    with cf.ThreadPoolExecutor(20) as ex:
        res = list(ex.map(lambda u: timed(lambda: mock_flow(u)), users))
    failures += report("mock sessions", res, time.time() - t0)

    print(f"\n5xx or network errors: {failures}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
