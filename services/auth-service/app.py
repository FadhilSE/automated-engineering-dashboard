import os
import datetime as dt
import jwt
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

JWT_SECRET = os.environ.get("JWT_SECRET", "dev_secret_change_me")
DATABASE_URL = os.environ["DATABASE_URL"]

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow, nullable=False)

with app.app_context():
    db.create_all()

@app.get("/health")
def health():
    return {"status": "ok", "service": "auth-service"}

def make_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "exp": dt.datetime.utcnow() + dt.timedelta(hours=8),
        "iat": dt.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

@app.post("/register")
def register():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip() or "User"
    if not email or not password:
        return {"error": "email and password required"}, 400
    if User.query.filter_by(email=email).first():
        return {"error": "email already exists"}, 409
    user = User(email=email, name=name, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return {"id": user.id, "email": user.email, "name": user.name}, 201

@app.post("/login")
def login():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return {"error": "invalid credentials"}, 401
    token = make_token(user)
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name}}

@app.get("/me")
def me():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return {"error": "missing bearer token"}, 401
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return {"error": "invalid token"}, 401
    return {"user": {"id": payload["sub"], "email": payload["email"], "name": payload["name"]}}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
