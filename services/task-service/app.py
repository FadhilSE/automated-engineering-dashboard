import os
import datetime as dt
import requests
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from auth_client import require_user

DATABASE_URL = os.environ["DATABASE_URL"]
PROJECT_SERVICE_URL = os.environ.get("PROJECT_SERVICE_URL", "http://project-service:5002").rstrip("/")

VALID_STATUSES = {"TODO", "IN_PROGRESS", "DONE"}

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="TODO")
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    assigned_to = db.Column(db.Integer, nullable=True, index=True)
    created_by = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow, nullable=False)

with app.app_context():
    db.create_all()

@app.get("/health")
def health():
    return {"status": "ok", "service": "task-service"}

def require_project_member(project_id: int, auth_header: str):
    resp = requests.get(
        f"{PROJECT_SERVICE_URL}/{project_id}/authorize",
        headers={"Authorization": auth_header},
        timeout=10,
    )
    if resp.status_code != 200:
        return False, None
    data = resp.json()
    return bool(data.get("authorized")), data.get("user")

def serialize(t: Task) -> dict:
    return {
        "id": t.id,
        "project_id": t.project_id,
        "title": t.title,
        "status": t.status,
        "description": t.description,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "assigned_to": t.assigned_to,
        "created_by": t.created_by,
        "created_at": t.created_at.isoformat(),
    }

def parse_due_date(value):
    if not value:
        return None
    return dt.date.fromisoformat(value)

def normalize_status(value):
    status = (value or "TODO").strip().upper()
    if status not in VALID_STATUSES:
        raise ValueError("invalid status")
    return status

@app.post("/projects/<int:project_id>/tasks")
def create_task(project_id: int):
    auth = request.headers.get("Authorization", "")
    ok, user = require_project_member(project_id, auth)
    if not ok:
        return {"error": "forbidden"}, 403
    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    if not title:
        return {"error": "title required"}, 400
    try:
        status = normalize_status(data.get("status") or "TODO")
        due = parse_due_date(data.get("due_date"))
    except ValueError as exc:
        return {"error": str(exc)}, 400
    t = Task(
        project_id=project_id,
        title=title,
        status=status,
        description=(data.get("description") or "").strip(),
        due_date=due,
        assigned_to=int(data["assigned_to"]) if data.get("assigned_to") else None,
        created_by=int(user["id"]),
    )
    db.session.add(t)
    db.session.commit()
    return {"task": serialize(t)}, 201

@app.get("/projects/<int:project_id>/tasks")
def list_tasks(project_id: int):
    auth = request.headers.get("Authorization", "")
    ok, _ = require_project_member(project_id, auth)
    if not ok:
        return {"error": "forbidden"}, 403
    tasks = Task.query.filter_by(project_id=project_id).order_by(Task.id.asc()).all()
    return {"tasks": [serialize(t) for t in tasks]}

@app.put("/tasks/<int:task_id>")
def update_task(task_id: int):
    auth = request.headers.get("Authorization", "")
    task = Task.query.get_or_404(task_id)
    ok, _ = require_project_member(task.project_id, auth)
    if not ok:
        return {"error": "forbidden"}, 403
    data = request.get_json(force=True)

    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return {"error": "title required"}, 400
        task.title = title
    if "description" in data:
        task.description = (data.get("description") or "").strip()
    if "status" in data:
        try:
            task.status = normalize_status(data.get("status"))
        except ValueError as exc:
            return {"error": str(exc)}, 400
    if "due_date" in data:
        try:
            task.due_date = parse_due_date(data.get("due_date"))
        except ValueError:
            return {"error": "invalid due_date"}, 400
    if "assigned_to" in data:
        task.assigned_to = int(data["assigned_to"]) if data.get("assigned_to") else None

    db.session.commit()
    return {"task": serialize(task)}

@app.delete("/tasks/<int:task_id>")
def delete_task(task_id: int):
    auth = request.headers.get("Authorization", "")
    task = Task.query.get_or_404(task_id)
    ok, _ = require_project_member(task.project_id, auth)
    if not ok:
        return {"error": "forbidden"}, 403
    db.session.delete(task)
    db.session.commit()
    return {"deleted": True, "task_id": task_id}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
