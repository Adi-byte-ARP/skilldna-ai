"""Security regressions found in the scale test: cross-user access, unsafe
upload filenames, and the legacy user-creation endpoint."""
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/skilldna_security_{uuid.uuid4().hex}.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.utils.files import clean_filename, stored_filename  # noqa: E402

client = TestClient(app)


def _user():
    email = f"sec{uuid.uuid4().hex[:12]}@gmail.com"
    r = client.post("/auth/register", json={"name": "Sec Tester", "email": email, "password": "TestPass123!"})
    body = r.json()
    return body["user"]["id"], {"Authorization": f"Bearer {body['token']}"}


def test_report_requires_login():
    uid, _ = _user()
    assert client.get(f"/report/{uid}").status_code == 401


def test_user_cannot_read_another_users_report():
    alice, _ = _user()
    _, bob_headers = _user()
    assert client.get(f"/report/{alice}", headers=bob_headers).status_code == 403


def test_user_can_read_own_report():
    uid, headers = _user()
    assert client.get(f"/report/{uid}", headers=headers).status_code == 200


def test_user_cannot_upload_into_another_users_account():
    alice, _ = _user()
    _, bob_headers = _user()
    r = client.post(f"/resume/upload/{alice}", headers=bob_headers,
                    files={"file": ("cv.pdf", b"%PDF-1.4 fake", "application/pdf")})
    assert r.status_code == 403


def test_user_profile_lookup_is_private():
    uid, _ = _user()
    _, other = _user()
    assert client.get(f"/users/{uid}", headers=other).status_code == 403


def test_legacy_user_creation_is_disabled():
    r = client.post("/users", json={"name": "x", "email": "someone@example.com"})
    assert r.status_code == 410


def test_health_endpoint_available():
    assert client.get("/health").json() == {"status": "healthy"}


def test_filenames_are_sanitized():
    assert "/" not in clean_filename("../../evil.pdf")
    assert clean_filename("../../evil.pdf") == "evil.pdf"
    assert clean_filename("my cv (final)!.pdf") == "my_cv__final__.pdf"
    assert clean_filename("") == "upload"
    assert len(clean_filename("a" * 500)) <= 80
    assert stored_filename("../x.pdf").endswith("_x.pdf")


def test_hostile_upload_filename_does_not_crash():
    uid, headers = _user()
    r = client.post(f"/resume/upload/{uid}", headers=headers,
                    files={"file": ("../../evil.pdf", b"%PDF-1.4 not really", "application/pdf")})
    assert r.status_code != 500


def test_report_reads_do_not_write_and_stay_consistent():
    """Regression for the scale-test 500s: repeated and concurrent reads must
    all succeed, even while the user has data on file."""
    from concurrent.futures import ThreadPoolExecutor
    uid, headers = _user()
    client.post(f"/resume/upload/{uid}", headers=headers,
                files={"file": ("cv.pdf", b"%PDF-1.4 not a real resume", "application/pdf")})
    with ThreadPoolExecutor(16) as ex:
        codes = list(ex.map(lambda _: client.get(f"/report/{uid}", headers=headers).status_code, range(48)))
    assert set(codes) == {200}
