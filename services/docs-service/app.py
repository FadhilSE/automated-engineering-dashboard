import os
import uuid
import datetime as dt
import requests
from flask import Flask, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from auth_client import require_user

DATABASE_URL = os.environ["DATABASE_URL"]
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/data/uploads")
PROJECT_SERVICE_URL = os.environ.get("PROJECT_SERVICE_URL", "http://project-service:5002").rstrip("/")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Document(db.Model):
    __tablename__ = "documents"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    kind = db.Column(db.String(30), nullable=False, default="file")  # file/link
    file_name = db.Column(db.String(255), nullable=True)
    link_url = db.Column(db.Text, nullable=True)
    uploaded_by = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow, nullable=False)

with app.app_context():
    db.create_all()

os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/health")
def health():
    return {"status": "ok", "service": "docs-service"}

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

def serialize(d: Document) -> dict:
    file_size = None
    if d.kind == "file" and d.file_name:
        path = os.path.join(UPLOAD_DIR, d.file_name)
        if os.path.exists(path):
            file_size = os.path.getsize(path)
    return {
        "id": d.id,
        "project_id": d.project_id,
        "title": d.title,
        "kind": d.kind,
        "file_name": d.file_name,
        "link_url": d.link_url,
        "uploaded_by": d.uploaded_by,
        "created_at": d.created_at.isoformat(),
        "file_size": file_size,
    }

@app.post("/projects/<int:project_id>/docs")
def create_doc(project_id: int):
    auth = request.headers.get("Authorization", "")
    ok, user = require_project_member(project_id, auth)
    if not ok:
        return {"error": "forbidden"}, 403

    if "file" in request.files:
        f = request.files["file"]
        if not f.filename:
            return {"error": "no file selected"}, 400
        title = (request.form.get("title") or f.filename).strip()
        original_name = secure_filename(f.filename)
        stored_name = f"{uuid.uuid4().hex}_{original_name}"
        f.save(os.path.join(UPLOAD_DIR, stored_name))
        doc = Document(project_id=project_id, title=title, kind="file", file_name=stored_name, uploaded_by=int(user["id"]))
        db.session.add(doc)
        db.session.commit()
        return {"document": serialize(doc)}, 201

    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    link = (data.get("link_url") or "").strip()
    if not title or not link:
        return {"error": "title and link_url required (or upload file)"}, 400
    doc = Document(project_id=project_id, title=title, kind="link", link_url=link, uploaded_by=int(user["id"]))
    db.session.add(doc)
    db.session.commit()
    return {"document": serialize(doc)}, 201

@app.get("/projects/<int:project_id>/docs")
def list_docs(project_id: int):
    auth = request.headers.get("Authorization", "")
    ok, _ = require_project_member(project_id, auth)
    if not ok:
        return {"error": "forbidden"}, 403
    docs = Document.query.filter_by(project_id=project_id).order_by(Document.id.asc()).all()
    return {"documents": [serialize(d) for d in docs]}

@app.patch("/docs/<int:doc_id>")
def update_doc(doc_id: int):
    auth = request.headers.get("Authorization", "")
    doc = Document.query.get_or_404(doc_id)
    ok, _ = require_project_member(doc.project_id, auth)
    if not ok:
        return {"error": "forbidden"}, 403
    data = request.get_json(force=True)
    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return {"error": "title required"}, 400
        doc.title = title
    if doc.kind == "link" and "link_url" in data:
        link = (data.get("link_url") or "").strip()
        if not link:
            return {"error": "link_url required"}, 400
        doc.link_url = link
    db.session.commit()
    return {"document": serialize(doc)}

@app.delete("/docs/<int:doc_id>")
def delete_doc(doc_id: int):
    auth = request.headers.get("Authorization", "")
    doc = Document.query.get_or_404(doc_id)
    ok, _ = require_project_member(doc.project_id, auth)
    if not ok:
        return {"error": "forbidden"}, 403
    file_path = os.path.join(UPLOAD_DIR, doc.file_name) if doc.kind == "file" and doc.file_name else None
    db.session.delete(doc)
    db.session.commit()
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    return {"deleted": True, "doc_id": doc_id}

@app.get("/docs/<int:doc_id>/download")
def download(doc_id: int):
    auth = request.headers.get("Authorization", "")
    doc = Document.query.get_or_404(doc_id)
    ok, _ = require_project_member(doc.project_id, auth)
    if not ok:
        return {"error": "forbidden"}, 403
    if doc.kind != "file" or not doc.file_name:
        return {"error": "not a file document"}, 400
    return send_from_directory(UPLOAD_DIR, doc.file_name, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004, debug=True)
