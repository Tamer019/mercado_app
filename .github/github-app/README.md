GitHub App manifest and helper to fetch issues

What this provides
- manifest.yml: a GitHub App manifest you can use to create the App via "From manifest" in the GitHub UI.
- fetch_issues_app.py: a Python helper (infra/github_app) that exchanges the App private key for an installation token and lists issues.

Installation steps
1. Create the App from the manifest
   - Go to https://github.com/settings/apps/new
   - Choose "From manifest" and paste the contents of `.github/github-app/manifest.yml`
   - Set a webhook URL (or leave placeholder) and create the App
2. Generate and download the private key (private-key.pem) from the App settings
3. Install the App on this repository (choose the repository and grant permissions)
   - After installing, note the installation ID from the URL or via the API
4. Run the helper locally
   - Put the private key next to the script or set `GITHUB_APP_PRIVATE_KEY` to its path
   - Export env vars: `GITHUB_APP_ID`, `GITHUB_INSTALLATION_ID`, `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME`
   - Install deps: `pip install -r requirements.txt PyJWT requests` (requirements.txt updated to include PyJWT)
   - Run: `python infra/github_app/fetch_issues_app.py`

Security notes
- Keep the private key secret. Do not commit it to the repo.
- The App manifest grants only read access to issues/contents/metadata; adjust if you need write access.

If you want, I can also:
- Create a minimal GitHub Actions workflow that uses the App (via secrets) to fetch issues on demand.
- Add a script to exchange the App's JWT for an installation token and save it into the environment automatically.
