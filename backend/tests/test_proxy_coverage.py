"""Every API route prefix must be forwarded by the Vite dev proxy.

A missing prefix sends the request to the dev server, which answers 404 or index.html, so a
feature works in production and fails silently in development. This test keeps the two in step.
"""
from pathlib import Path

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED = {"docs", "redoc", "openapi.json"}


def _api_prefixes():
    prefixes = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        first = path.strip("/").split("/")[0]
        if first and first not in EXCLUDED:
            prefixes.add("/" + first)
    return prefixes


def test_vite_proxy_forwards_every_api_prefix():
    config = (ROOT / "frontend" / "vite.config.js").read_text(encoding="utf-8")
    missing = sorted(p for p in _api_prefixes() if f"'{p}'" not in config)
    assert not missing, f"add these to the Vite proxy in frontend/vite.config.js: {missing}"
