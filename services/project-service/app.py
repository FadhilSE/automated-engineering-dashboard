import os
import datetime as dt
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from auth_client import require_user

DATABASE_URL = os.environ["DATABASE_URL"]

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    github_repo = db.Column(db.String(255), nullable=True)
    owner_user_id = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow, nullable=False)

class ProjectMember(db.Model):
    __tablename__ = "project_members"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    role = db.Column(db.String(50), nullable=False, default="member")
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow, nullable=False)

with app.app_context():
    db.create_all()
    inspector = db.inspect(db.engine)
    columns = {c["name"] for c in inspector.get_columns("projects")}
    if "github_repo" not in columns:
        db.session.execute(text("ALTER TABLE projects ADD COLUMN github_repo VARCHAR(255)"))
        db.session.commit()


def serialize_project(p: Project) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "github_repo": p.github_repo,
        "owner_user_id": p.owner_user_id,
        "created_at": p.created_at.isoformat(),
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "project-service"}

@app.post("/")
def create_project():
    user = require_user(request.headers.get("Authorization", ""))
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    desc = (data.get("description") or "").strip()
    github_repo = (data.get("github_repo") or "").strip() or None
    if not name:
        return {"error": "name required"}, 400
    p = Project(name=name, description=desc, github_repo=github_repo, owner_user_id=int(user["id"]))
    db.session.add(p)
    db.session.commit()
    db.session.add(ProjectMember(project_id=p.id, user_id=int(user["id"]), role="owner"))
    db.session.commit()
    return serialize_project(p), 201

@app.get("/")
def list_projects():
    user = require_user(request.headers.get("Authorization", ""))
    uid = int(user["id"])
    ids = [m.project_id for m in ProjectMember.query.filter_by(user_id=uid).all()]
    projects = Project.query.filter(Project.id.in_(ids)).order_by(Project.created_at.desc(), Project.id.desc()).all()
    return {"projects": [serialize_project(p) for p in projects]}

@app.get("/<int:project_id>")
def get_project(project_id: int):
    user = require_user(request.headers.get("Authorization", ""))
    uid = int(user["id"])
    member = ProjectMember.query.filter_by(project_id=project_id, user_id=uid).first()
    if member is None:
        return {"error": "forbidden"}, 403
    project = Project.query.get_or_404(project_id)
    return {"project": serialize_project(project), "membership_role": member.role}

@app.patch("/<int:project_id>")
def update_project(project_id: int):
    user = require_user(request.headers.get("Authorization", ""))
    uid = int(user["id"])
    member = ProjectMember.query.filter_by(project_id=project_id, user_id=uid).first()
    if member is None:
        return {"error": "forbidden"}, 403
    project = Project.query.get_or_404(project_id)
    data = request.get_json(force=True)

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return {"error": "name required"}, 400
        project.name = name
    if "description" in data:
        project.description = (data.get("description") or "").strip()
    if "github_repo" in data:
        project.github_repo = (data.get("github_repo") or "").strip() or None

    db.session.commit()
    return {"project": serialize_project(project), "membership_role": member.role}

@app.get("/<int:project_id>/authorize")
def authorize(project_id: int):
    user = require_user(request.headers.get("Authorization", ""))
    uid = int(user["id"])
    member = ProjectMember.query.filter_by(project_id=project_id, user_id=uid).first()
    ok = member is not None
    return {"authorized": ok, "user": user, "membership_role": member.role if member else None}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
