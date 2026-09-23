# Contributing

Thanks for wanting to help improve SkillDNA — small, focused contributions are welcome.

Getting started
- Fork the repo and create a feature branch: `git checkout -b feat/your-feature`
- Keep changes small and focused; open a single PR per logical change.

Code style
- Backend: follow existing project layout and type hints. Run `pytest` before opening a PR.
- Frontend: follow React component patterns in `frontend/src/components`.

Testing
- Backend tests: `cd backend && pytest -q`
- Frontend build: `cd frontend && npm ci && npm run build`

Daily updates
- Add short diary-like notes to `CHANGELOG.md` under an unreleased heading each day.

Thank you — maintainers will review PRs and leave actionable feedback.
