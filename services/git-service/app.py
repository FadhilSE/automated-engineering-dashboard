import os
import re
import requests
from flask import Flask, request

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or ""
AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:5001").rstrip("/")

app = Flask(__name__)

@app.get("/health")
def health():
    return {"status": "ok", "service": "git-service"}

def require_user(auth_header: str):
    resp = requests.get(AUTH_SERVICE_URL + "/me", headers={"Authorization": auth_header}, timeout=10)
    if resp.status_code != 200:
        raise ValueError("invalid token")
    return resp.json()["user"]

def normalize_repo(value: str) -> str:
    repo = (value or "").strip()
    repo = repo.removesuffix('.git')
    if repo.startswith('https://github.com/'):
        repo = repo.split('https://github.com/', 1)[1]
    repo = repo.strip('/')
    if not re.fullmatch(r'[^/\s]+/[^/\s]+', repo):
        raise ValueError('repo query param required like owner/repo or https://github.com/owner/repo')
    return repo

@app.get("/github/commits")
def github_commits():
    auth = request.headers.get("Authorization", "")
    try:
        _user = require_user(auth)
    except Exception:
        return {"error": "unauthorized"}, 401

    try:
        repo = normalize_repo(request.args.get("repo") or "")
    except ValueError as exc:
        return {"error": str(exc)}, 400

    per_page = min(max(int(request.args.get("per_page") or 5), 1), 20)
    url = f"https://api.github.com/repos/{repo}/commits"
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    r = requests.get(url, headers=headers, params={"per_page": per_page}, timeout=15)
    if r.status_code == 404:
        return {"error": "repository not found"}, 404
    if r.status_code != 200:
        return {"error": "github api error", "status": r.status_code}, 502

    commits = []
    for c in r.json():
        commits.append({
            "sha": c.get("sha"),
            "short_sha": (c.get("sha") or "")[:7],
            "message": (c.get("commit") or {}).get("message"),
            "author": ((c.get("commit") or {}).get("author") or {}).get("name"),
            "date": ((c.get("commit") or {}).get("author") or {}).get("date"),
            "html_url": c.get("html_url"),
        })
    return {"repo": repo, "commits": commits}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
