import os
from flask import Flask, render_template

app = Flask(__name__, template_folder="templates", static_folder="static")
GATEWAY_BASE = os.environ.get("GATEWAY_BASE", "http://localhost:8080")

@app.get("/health")
def health():
    return {"status": "ok", "service": "web-ui"}

@app.get("/")
def login_page():
    return render_template("login.html", gateway_base=GATEWAY_BASE)

@app.get("/dashboard")
def dashboard_page():
    return render_template("dashboard.html", gateway_base=GATEWAY_BASE)

@app.get("/projects")
def projects_page():
    return render_template("projects.html", gateway_base=GATEWAY_BASE)

@app.get("/projects/<int:project_id>")
def project_detail(project_id: int):
    return render_template("project_detail.html", gateway_base=GATEWAY_BASE, project_id=project_id)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
