import os
import requests
from flask import Flask, request
from datetime import date

AUTH = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:5001").rstrip("/")
PROJECTS = os.environ.get("PROJECT_SERVICE_URL", "http://project-service:5002").rstrip("/")
TASKS = os.environ.get("TASK_SERVICE_URL", "http://task-service:5003").rstrip("/")
DOCS = os.environ.get("DOCS_SERVICE_URL", "http://docs-service:5004").rstrip("/")

app = Flask(__name__)

@app.get("/health")
def health():
    return {"status": "ok", "service": "analytics-service"}

def require_user(auth_header: str):
    resp = requests.get(AUTH + "/me", headers={"Authorization": auth_header}, timeout=10)
    if resp.status_code != 200:
        raise ValueError("invalid token")
    return resp.json()["user"]

def task_breakdown(tasks):
    total = len(tasks)
    done = sum(1 for x in tasks if (x.get("status") or "").upper() == "DONE")
    in_prog = sum(1 for x in tasks if (x.get("status") or "").upper() == "IN_PROGRESS")
    todo = sum(1 for x in tasks if (x.get("status") or "").upper() == "TODO")
    overdue = 0
    due_soon = []
    for x in tasks:
        dd = x.get("due_date")
        if dd and (x.get("status") or "").upper() != "DONE":
            try:
                due = date.fromisoformat(dd)
                if due < date.today():
                    overdue += 1
                due_soon.append({**x, "days_until_due": (due - date.today()).days})
            except Exception:
                pass
    due_soon.sort(key=lambda x: (x.get("days_until_due", 10**9), x.get("id", 10**9)))
    return {
        "total": total,
        "todo": todo,
        "in_progress": in_prog,
        "done": done,
        "overdue": overdue,
        "progress_percent": int((done / total) * 100) if total else 0,
        "due_soon": due_soon[:5],
    }

@app.get("/projects/<int:project_id>/metrics")
def metrics(project_id: int):
    auth = request.headers.get("Authorization", "")
    try:
        _user = require_user(auth)
    except Exception:
        return {"error": "unauthorized"}, 401

    authz = requests.get(f"{PROJECTS}/{project_id}/authorize", headers={"Authorization": auth}, timeout=10)
    if authz.status_code != 200 or not authz.json().get("authorized"):
        return {"error": "forbidden"}, 403

    project_resp = requests.get(f"{PROJECTS}/{project_id}", headers={"Authorization": auth}, timeout=10)
    project = project_resp.json().get("project") if project_resp.status_code == 200 else None

    t = requests.get(f"{TASKS}/projects/{project_id}/tasks", headers={"Authorization": auth}, timeout=15)
    tasks = (t.json().get("tasks") if t.status_code == 200 else []) or []

    d = requests.get(f"{DOCS}/projects/{project_id}/docs", headers={"Authorization": auth}, timeout=15)
    docs = (d.json().get("documents") if d.status_code == 200 else []) or []

    breakdown = task_breakdown(tasks)
    return {
        "project_id": project_id,
        "project": project,
        "tasks": {
            "total": breakdown["total"],
            "todo": breakdown["todo"],
            "in_progress": breakdown["in_progress"],
            "done": breakdown["done"],
            "overdue": breakdown["overdue"],
        },
        "documents": {"count": len(docs)},
        "progress_percent": breakdown["progress_percent"],
        "due_soon": breakdown["due_soon"],
    }

@app.get("/dashboard/summary")
def dashboard_summary():
    auth = request.headers.get("Authorization", "")
    try:
        user = require_user(auth)
    except Exception:
        return {"error": "unauthorized"}, 401

    p_resp = requests.get(f"{PROJECTS}/", headers={"Authorization": auth}, timeout=15)
    if p_resp.status_code != 200:
        return {"error": "failed to load projects"}, 502
    projects = (p_resp.json().get("projects") or [])

    summary = {
        "user": user,
        "projects_count": len(projects),
        "tasks": {"total": 0, "todo": 0, "in_progress": 0, "done": 0, "overdue": 0},
        "documents_count": 0,
        "overall_progress_percent": 0,
        "projects": [],
        "upcoming_deadlines": [],
    }

    all_total = 0
    all_done = 0
    for project in projects:
        pid = project["id"]
        t_resp = requests.get(f"{TASKS}/projects/{pid}/tasks", headers={"Authorization": auth}, timeout=15)
        d_resp = requests.get(f"{DOCS}/projects/{pid}/docs", headers={"Authorization": auth}, timeout=15)
        tasks = (t_resp.json().get("tasks") if t_resp.status_code == 200 else []) or []
        docs = (d_resp.json().get("documents") if d_resp.status_code == 200 else []) or []
        breakdown = task_breakdown(tasks)

        summary["tasks"]["total"] += breakdown["total"]
        summary["tasks"]["todo"] += breakdown["todo"]
        summary["tasks"]["in_progress"] += breakdown["in_progress"]
        summary["tasks"]["done"] += breakdown["done"]
        summary["tasks"]["overdue"] += breakdown["overdue"]
        summary["documents_count"] += len(docs)
        all_total += breakdown["total"]
        all_done += breakdown["done"]

        project_summary = {
            "id": pid,
            "name": project.get("name"),
            "description": project.get("description"),
            "github_repo": project.get("github_repo"),
            "created_at": project.get("created_at"),
            "tasks": {
                "total": breakdown["total"],
                "done": breakdown["done"],
                "overdue": breakdown["overdue"],
            },
            "documents_count": len(docs),
            "progress_percent": breakdown["progress_percent"],
        }
        summary["projects"].append(project_summary)

        for task in breakdown["due_soon"]:
            summary["upcoming_deadlines"].append({
                "project_id": pid,
                "project_name": project.get("name"),
                "task_id": task.get("id"),
                "task_title": task.get("title"),
                "due_date": task.get("due_date"),
                "days_until_due": task.get("days_until_due"),
                "status": task.get("status"),
            })

    summary["overall_progress_percent"] = int((all_done / all_total) * 100) if all_total else 0
    summary["projects"].sort(key=lambda x: (-(x.get("tasks", {}).get("overdue", 0)), x.get("name") or ""))
    summary["upcoming_deadlines"].sort(key=lambda x: (x.get("days_until_due", 10**9), x.get("project_id", 10**9)))
    summary["upcoming_deadlines"] = summary["upcoming_deadlines"][:8]
    return summary

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5006, debug=True)
