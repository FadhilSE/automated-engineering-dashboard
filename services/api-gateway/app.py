import os
import requests
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

AUTH = os.environ["AUTH_SERVICE_URL"].rstrip("/")
PROJECTS = os.environ["PROJECT_SERVICE_URL"].rstrip("/")
TASKS = os.environ["TASK_SERVICE_URL"].rstrip("/")
DOCS = os.environ["DOCS_SERVICE_URL"].rstrip("/")
GIT = os.environ["GIT_SERVICE_URL"].rstrip("/")
ANALYTICS = os.environ["ANALYTICS_SERVICE_URL"].rstrip("/")

ROUTES = [
    ("/api/auth", AUTH),
    ("/api/projects", PROJECTS),
    ("/api/tasks", TASKS),
    ("/api/docs", DOCS),
    ("/api/git", GIT),
    ("/api/analytics", ANALYTICS),
]

@app.get("/health")
def health():
    return {"status": "ok", "service": "api-gateway"}

def _proxy(target_base: str, path_suffix: str):
    url = target_base + path_suffix
    headers = {k: v for k, v in request.headers if k.lower() != "host"}

    resp = requests.request(
        method=request.method,
        url=url,
        headers=headers,
        params=request.args,
        data=request.get_data(),
        allow_redirects=False,
        timeout=20,
    )

    excluded = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    out_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded]
    return Response(resp.content, resp.status_code, out_headers)

@app.route("/api/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def route_api(path: str):
    if request.method == "OPTIONS":
        return ("", 204)

    full = "/api/" + path
    for prefix, base in ROUTES:
        if full.startswith(prefix):
            suffix = full[len(prefix):]
            if not suffix.startswith("/"):
                suffix = "/" + suffix
            return _proxy(base, suffix)

    return jsonify({"error": "No route for path", "path": full}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)