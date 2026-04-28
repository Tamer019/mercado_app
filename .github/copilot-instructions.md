# Copilot instructions for mercado_app

Purpose
- Help Copilot sessions quickly understand how to run, test, and navigate this repository.

Build / run / test
- Activate the included venv (macOS/Linux):
  `source venv/bin/activate`
- Install dependencies from the repo requirements:
  `pip install -r requirements.txt`
- Run backend (development):
  `uvicorn api.main:app --reload --host 127.0.0.1 --port 8000`
  - The FastAPI app exposes `/search?q=...&plz=...` and proxies requests to the Marktguru API.
- Serve the static frontend (optional) so it can fetch the backend from a browser:
  `python -m http.server 8001 --directory frontend`
  then open `http://127.0.0.1:8001/`.
- Run a single scraper/debug script:
  `python scraper/test_api.py`
- Quick smoke API call (single request):
  `curl "http://127.0.0.1:8000/search?q=mango&plz=72555"`
- Lint / tests: No centralized test runner or lint config detected. The repository does not include pytest/flake8 configs; scraper scripts are ad-hoc.

Environment / secrets
- The repository currently contains MARKETGURU API keys in `api/main.py` and `scraper/*.py`. Rotate and move these to environment variables before sharing.
- Recommended env var names (not implemented in code):
  - MARKTGURU_X_CLIENTKEY
  - MARKTGURU_X_APIKEY
  Example run with env vars (after updating code to read them):
  `MARKTGURU_X_CLIENTKEY=... MARKTGURU_X_APIKEY=... uvicorn api.main:app --reload`

High-level architecture
- Frontend (frontend/index.html): static single-page UI (vanilla JS). It calls the backend at `http://127.0.0.1:8000/search` and expects JSON with a compact result list.
- Backend (api/main.py): FastAPI app that queries the external Marktguru API and returns a simplified JSON payload. CORS is configured permissively for local development.
- Scraper (scraper/): small, standalone Python scripts used to inspect the third-party API and debug responses.
- Infra utilities (infra/github_app): helper scripts for GitHub App integrations (e.g., fetch_issues_app.py requires GITHUB_APP_ID, GITHUB_INSTALLATION_ID, and a private key path).

Key conventions and repo-specific notes
- Secrets-in-code: API keys are checked in. Prioritize moving them to env vars or a secrets manager.
- CORS: api/main.py sets allow_origins=["*"] for ease of local dev — be cautious when deploying.
- Local dev assumptions:
  - Frontend expects the backend at 127.0.0.1:8000.
  - Frontend is static and does not use a build step; use a simple HTTP server to serve `frontend/` during testing.
- Scraper scripts (`scraper/test_*.py`) are exploratory and print results to stdout; run individually.
- infra/github_app/fetch_issues_app.py demonstrates how to create a GitHub App JWT and list issues. Set env vars: GITHUB_APP_ID, GITHUB_INSTALLATION_ID, GITHUB_APP_PRIVATE_KEY, GITHUB_REPO_OWNER, GITHUB_REPO_NAME.

AI assistant / other tool configs
- No other AI assistant config files were detected (checked for CLAUDE.md, .cursorrules, .cursor/, AGENTS.md, CONVENTIONS.md, .windsurfrules, .clinerules).

When editing
- Avoid committing secrets. If migrating keys to env vars, add a short README note and do not commit real keys.
- If adding CI or linters, document install and run commands here (e.g., `pip install -r requirements-dev.txt` and `flake8`).

Location and intent
- File: `.github/copilot-instructions.md`
- Intent: give future Copilot sessions a concise, repo-specific summary (how to run, what to expect, and notable pitfalls) so suggestions are accurate and actionable.

Next steps
- Consider updating api/main.py to read API keys from environment variables and adding a tiny README snippet showing how to set them.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>