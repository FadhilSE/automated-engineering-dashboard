window.GATEWAY_BASE = "http://localhost:8080";

const tokenKey = "aed_token";
const userKey = "aed_user";

function saveAuth(token, user) {
  localStorage.setItem(tokenKey, token);
  localStorage.setItem(userKey, JSON.stringify(user || null));
}
function getToken() { return localStorage.getItem(tokenKey) || ""; }
function getUser() {
  try { return JSON.parse(localStorage.getItem(userKey) || "null"); } catch { return null; }
}
function logout() {
  localStorage.removeItem(tokenKey);
  localStorage.removeItem(userKey);
  window.location.href = "/";
}
function authHeaders(extra = {}) {
  const token = getToken();
  return token ? { ...extra, Authorization: `Bearer ${token}` } : { ...extra };
}
async function api(path, options = {}) {
  const res = await fetch((window.GATEWAY_BASE || "") + path, options);
  let data = null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) data = await res.json();
  return { ok: res.ok, status: res.status, data };
}
function showLogoutIfToken() {
  const btn = document.getElementById("logoutBtn");
  if (!btn) return;
  btn.classList.toggle("d-none", !getToken());
}

async function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const msg = document.getElementById("msg");
  msg.textContent = "Logging in...";
  const res = await api("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  if (res.ok) {
    saveAuth(res.data.token, res.data.user);
    window.location.href = "/dashboard";
  } else {
    msg.textContent = res.data?.error || "Login failed";
  }
}

async function registerUser() {
  const name = document.getElementById("name")?.value?.trim() || "New User";
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const msg = document.getElementById("msg");
  msg.textContent = "Registering...";
  const res = await api("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password })
  });
  if (res.ok) {
    msg.textContent = "Registered. Now log in.";
  } else {
    msg.textContent = res.data?.error || "Registration failed";
  }
}

async function loadProjects() {
  const list = document.getElementById("projectsList");
  if (!list) return;
  list.innerHTML = '<div class="text-muted small">Loading projects...</div>';
  const res = await api("/api/projects/", { headers: authHeaders() });
  if (!res.ok) {
    list.innerHTML = `<div class="text-danger small">${res.data?.error || "Failed to load projects"}</div>`;
    return;
  }
  const projects = res.data.projects || [];
  if (!projects.length) {
    list.innerHTML = '<div class="text-muted small">No projects yet. Create one below.</div>';
    return;
  }
  list.innerHTML = "";
  for (const p of projects) {
    const a = document.createElement("a");
    a.href = `/projects/${p.id}`;
    a.className = "list-group-item list-group-item-action border-0 border-bottom py-3";
    a.innerHTML = `<div class="d-flex w-100 justify-content-between align-items-start gap-3">
      <div>
        <div class="fw-semibold">${escapeHtml(p.name)}</div>
        <div class="small text-muted">${escapeHtml(p.description || "No description")}</div>
        ${p.github_repo ? `<div class="small mt-1"><span class="badge text-bg-light">${escapeHtml(p.github_repo)}</span></div>` : ""}
      </div>
      <div class="text-muted small text-nowrap">#${p.id}</div>
    </div>`;
    list.appendChild(a);
  }
}

function openCreateProject() {
  const input = document.getElementById("projName");
  if (input) input.focus();
}
function clearProjectForm() {
  for (const id of ["projName", "projDesc", "projRepo"]) {
    const el = document.getElementById(id);
    if (el) el.value = "";
  }
  const msg = document.getElementById("createProjectMsg");
  if (msg) {
    msg.className = "small ms-2";
    msg.textContent = "";
  }
}

async function createProject() {
  const name = document.getElementById("projName").value.trim();
  const description = document.getElementById("projDesc").value.trim();
  const github_repo = document.getElementById("projRepo")?.value.trim() || null;
  const msg = document.getElementById("createProjectMsg");
  msg.className = "small mt-2";
  msg.textContent = "Creating...";
  const res = await api("/api/projects/", {
    method: "POST",
    headers: { ...authHeaders({ "Content-Type": "application/json" }) },
    body: JSON.stringify({ name, description, github_repo })
  });
  msg.classList.add(res.ok ? "text-success" : "text-danger");
  msg.textContent = res.ok ? "Project created!" : (res.data?.error || "Failed");
  if (res.ok) {
    clearProjectForm();
    await loadProjects();
    await loadDashboardSummary();
  }
}

async function loadDashboardSummary() {
  const metrics = {
    projects: document.getElementById("metricProjects"),
    tasks: document.getElementById("metricTasks"),
    docs: document.getElementById("metricDocs"),
    progress: document.getElementById("metricProgress")
  };
  if (!metrics.projects) return;

  const res = await api("/api/analytics/dashboard/summary", { headers: authHeaders() });
  const alert = document.getElementById("dashboardAlert");
  if (!res.ok) {
    if (alert) alert.innerHTML = `<span class="text-danger">${res.data?.error || "Failed to load dashboard"}</span>`;
    return;
  }
  const s = res.data;
  if (alert) alert.innerHTML = `<span class="text-muted">Welcome${s.user?.name ? `, ${escapeHtml(s.user.name)}` : ""}. Here is your current portfolio view.</span>`;
  metrics.projects.textContent = s.projects_count;
  metrics.tasks.textContent = s.tasks.total;
  metrics.docs.textContent = s.documents_count;
  metrics.progress.textContent = `${s.overall_progress_percent}%`;
  setText("dashboardProjectsCount", `${s.projects_count} total`);
  setText("dashTodo", s.tasks.todo);
  setText("dashInProgress", s.tasks.in_progress);
  setText("dashDone", s.tasks.done);
  setText("dashOverdue", s.tasks.overdue);

  const grid = document.getElementById("dashboardProjectsGrid");
  if (grid) {
    if (!s.projects.length) {
      grid.innerHTML = '<div class="col-12"><div class="text-muted small">No projects yet. Create your first one from the Projects page.</div></div>';
    } else {
      grid.innerHTML = s.projects.map(p => `
        <div class="col-md-6">
          <div class="card border-0 bg-light h-100">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                  <h6 class="mb-1">${escapeHtml(p.name)}</h6>
                  <div class="small text-muted mb-2">${escapeHtml(p.description || "No description")}</div>
                </div>
                <a class="btn btn-sm btn-outline-primary" href="/projects/${p.id}">Open</a>
              </div>
              <div class="small d-flex justify-content-between"><span>Progress</span><strong>${p.progress_percent}%</strong></div>
              <div class="progress project-progress my-2"><div class="progress-bar" role="progressbar" style="width:${p.progress_percent}%"></div></div>
              <div class="small d-flex justify-content-between"><span>Tasks</span><span>${p.tasks.done}/${p.tasks.total} done</span></div>
              <div class="small d-flex justify-content-between"><span>Documents</span><span>${p.documents_count}</span></div>
              <div class="small d-flex justify-content-between"><span>Overdue</span><span class="${p.tasks.overdue ? "text-danger fw-semibold" : "text-muted"}">${p.tasks.overdue}</span></div>
              ${p.github_repo ? `<div class="small mt-2"><span class="badge text-bg-light">${escapeHtml(p.github_repo)}</span></div>` : ""}
            </div>
          </div>
        </div>`).join("");
    }
  }

  const deadlines = document.getElementById("dashboardDeadlines");
  if (deadlines) {
    if (!s.upcoming_deadlines.length) {
      deadlines.innerHTML = '<div class="text-muted small">No upcoming deadlines right now.</div>';
    } else {
      deadlines.innerHTML = s.upcoming_deadlines.map(item => `
        <a href="/projects/${item.project_id}" class="list-group-item list-group-item-action border-0 border-bottom px-0">
          <div class="fw-semibold small">${escapeHtml(item.task_title)}</div>
          <div class="small text-muted">${escapeHtml(item.project_name)} • ${escapeHtml(item.due_date || "No due date")}</div>
          <div class="small ${deadlineClass(item.days_until_due)}">${deadlineLabel(item.days_until_due)}</div>
        </a>`).join("");
    }
  }
}

async function loadProjectAll(projectId) {
  await Promise.all([
    loadProjectMeta(projectId),
    loadTasks(projectId),
    loadDocs(projectId),
    loadMetrics(projectId),
    loadRepoPanel(projectId)
  ]);
}

async function loadProjectMeta(projectId) {
  const title = document.getElementById("projectTitle");
  const meta = document.getElementById("projectMeta");
  if (meta) meta.textContent = "Loading project...";
  const res = await api(`/api/projects/${projectId}`, { headers: authHeaders() });
  if (!res.ok) {
    if (title) title.textContent = `Project #${projectId}`;
    if (meta) meta.textContent = res.data?.error || "Failed to load project";
    return;
  }
  const p = res.data.project;
  if (title) title.textContent = p.name;
  if (meta) {
    meta.textContent = `Project #${p.id} • Owner ${p.owner_user_id} • Created ${formatDateTime(p.created_at)} • Role: ${res.data.membership_role}`;
  }
  setText("projectDescription", p.description || "No description yet.");
  const repoInput = document.getElementById("projectRepo");
  if (repoInput) repoInput.value = p.github_repo || "";
}

async function saveProjectRepo(projectId) {
  const repo = document.getElementById("projectRepo")?.value.trim() || "";
  const msg = document.getElementById("projectRepoMsg");
  msg.className = "small mt-2";
  msg.textContent = "Saving...";
  const res = await api(`/api/projects/${projectId}`, {
    method: "PATCH",
    headers: { ...authHeaders({ "Content-Type": "application/json" }) },
    body: JSON.stringify({ github_repo: repo })
  });
  msg.classList.add(res.ok ? "text-success" : "text-danger");
  msg.textContent = res.ok ? "Repository saved." : (res.data?.error || "Failed to save repo");
  if (res.ok) {
    await loadProjectMeta(projectId);
    await loadRepoPanel(projectId);
    await loadDashboardSummary();
  }
}

async function loadRepoPanel(projectId) {
  const box = document.getElementById("repoCommitsBox");
  if (!box) return;
  const repo = document.getElementById("projectRepo")?.value.trim();
  if (!repo) {
    box.innerHTML = '<span class="text-muted">No repository connected yet.</span>';
    return;
  }
  box.innerHTML = '<span class="text-muted">Loading recent commits...</span>';
  const res = await api(`/api/git/github/commits?repo=${encodeURIComponent(repo)}&per_page=5`, { headers: authHeaders() });
  const msg = document.getElementById("projectRepoMsg");
  if (!res.ok) {
    if (msg) {
      msg.className = "small mt-2 text-danger";
      msg.textContent = res.data?.error || "Could not load commits";
    }
    box.innerHTML = '<span class="text-muted">No commit data available.</span>';
    return;
  }
  if (msg && msg.textContent === "Loading...") msg.textContent = "";
  const commits = res.data.commits || [];
  if (!commits.length) {
    box.innerHTML = '<span class="text-muted">No recent commits found.</span>';
    return;
  }
  box.innerHTML = `<div class="small mb-2"><strong>${escapeHtml(res.data.repo)}</strong></div>` + commits.map(c => `
    <div class="border rounded p-2 mb-2 bg-light">
      <div class="fw-semibold">${escapeHtml((c.message || "").split(String.fromCharCode(10))[0] || "No message")}</div>
      <div class="small text-muted">${escapeHtml(c.author || "Unknown author")} • ${formatDateTime(c.date)} • ${escapeHtml(c.short_sha || "")}</div>
      ${c.html_url ? `<a class="small" href="${escapeAttr(c.html_url)}" target="_blank" rel="noreferrer">View commit</a>` : ""}
    </div>`).join("");
}

async function loadTasks(projectId) {
  const wrap = document.getElementById("tasksTableWrap");
  if (!wrap) return;
  wrap.innerHTML = '<div class="text-muted small">Loading tasks...</div>';
  const res = await api(`/api/tasks/projects/${projectId}/tasks`, { headers: authHeaders() });
  if (!res.ok) {
    wrap.innerHTML = `<div class="text-danger small">${res.data?.error || "Failed to load tasks"}</div>`;
    return;
  }
  const tasks = res.data.tasks || [];
  setText("tasksCount", `${tasks.length} total`);
  wrap.innerHTML = renderTasksTable(tasks, projectId);
}

function renderTasksTable(tasks, projectId) {
  if (!tasks.length) return '<div class="text-muted small">No tasks yet.</div>';
  const statusOptions = ["TODO", "IN_PROGRESS", "DONE"];
  const rows = tasks.map(t => {
    const options = statusOptions.map(s => `<option value="${s}" ${t.status === s ? "selected" : ""}>${s}</option>`).join("");
    return `
    <tr>
      <td>${t.id}</td>
      <td>
        <div class="fw-semibold">${escapeHtml(t.title)}</div>
        <div class="text-muted small">${escapeHtml(t.description || "")}</div>
      </td>
      <td>
        <select class="form-select form-select-sm" id="task-status-${t.id}">${options}</select>
      </td>
      <td><input class="form-control form-control-sm" id="task-due-${t.id}" value="${escapeAttr(t.due_date || "")}" placeholder="YYYY-MM-DD"></td>
      <td>
        <div class="d-flex gap-2">
          <button class="btn btn-sm btn-outline-primary" onclick="updateTask(${projectId}, ${t.id})">Save</button>
          <button class="btn btn-sm btn-outline-danger" onclick="deleteTask(${projectId}, ${t.id})">Delete</button>
        </div>
        <div id="task-row-msg-${t.id}" class="small mt-1"></div>
      </td>
    </tr>`;
  }).join("");
  return `<div class="table-responsive">
    <table class="table table-sm align-middle">
      <thead><tr><th>ID</th><th>Task</th><th>Status</th><th>Due</th><th>Actions</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
}

async function createTask(projectId) {
  const title = document.getElementById("taskTitle").value.trim();
  const due_date = document.getElementById("taskDue").value.trim() || null;
  const status = document.getElementById("taskStatus").value;
  const description = document.getElementById("taskDesc").value.trim();
  const msg = document.getElementById("taskMsg");
  msg.className = "small mt-2";
  msg.textContent = "Creating...";
  const res = await api(`/api/tasks/projects/${projectId}/tasks`, {
    method: "POST",
    headers: { ...authHeaders({ "Content-Type": "application/json" }) },
    body: JSON.stringify({ title, due_date, status, description })
  });
  msg.classList.add(res.ok ? "text-success" : "text-danger");
  msg.textContent = res.ok ? "Task created!" : (res.data?.error || "Failed");
  if (res.ok) {
    document.getElementById("taskTitle").value = "";
    document.getElementById("taskDue").value = "";
    document.getElementById("taskDesc").value = "";
    await Promise.all([loadTasks(projectId), loadMetrics(projectId), loadDashboardSummary()]);
  }
}

async function updateTask(projectId, taskId) {
  const status = document.getElementById(`task-status-${taskId}`).value;
  const due_date = document.getElementById(`task-due-${taskId}`).value.trim() || null;
  const msg = document.getElementById(`task-row-msg-${taskId}`);
  msg.className = "small mt-1";
  msg.textContent = "Saving...";
  const res = await api(`/api/tasks/tasks/${taskId}`, {
    method: "PUT",
    headers: { ...authHeaders({ "Content-Type": "application/json" }) },
    body: JSON.stringify({ status, due_date })
  });
  msg.classList.add(res.ok ? "text-success" : "text-danger");
  msg.textContent = res.ok ? "Updated" : (res.data?.error || "Failed");
  if (res.ok) await Promise.all([loadTasks(projectId), loadMetrics(projectId), loadDashboardSummary()]);
}

async function deleteTask(projectId, taskId) {
  const msg = document.getElementById(`task-row-msg-${taskId}`);
  msg.className = "small mt-1";
  msg.textContent = "Deleting...";
  const res = await api(`/api/tasks/tasks/${taskId}`, {
    method: "DELETE",
    headers: authHeaders()
  });
  msg.classList.add(res.ok ? "text-success" : "text-danger");
  msg.textContent = res.ok ? "Deleted" : (res.data?.error || "Failed");
  if (res.ok) await Promise.all([loadTasks(projectId), loadMetrics(projectId), loadDashboardSummary()]);
}

async function loadDocs(projectId) {
  const list = document.getElementById("docsList");
  if (!list) return;
  list.innerHTML = '<div class="text-muted small">Loading docs...</div>';
  const res = await api(`/api/docs/projects/${projectId}/docs`, { headers: authHeaders() });
  if (!res.ok) {
    list.innerHTML = `<div class="text-danger small">${res.data?.error || "Failed to load docs"}</div>`;
    return;
  }
  const docs = res.data.documents || [];
  setText("docsCount", `${docs.length} total`);
  if (!docs.length) {
    list.innerHTML = '<div class="text-muted small">No documents yet.</div>';
    return;
  }
  list.innerHTML = "";
  for (const d of docs) {
    const item = document.createElement("div");
    item.className = "list-group-item border-0 border-bottom";
    const linkHtml = d.kind === "link"
      ? `<a href="${escapeAttr(d.link_url)}" target="_blank" rel="noreferrer">Open link</a>`
      : `<a href="${(window.GATEWAY_BASE||"")}/api/docs/docs/${d.id}/download" target="_blank">Download</a>`;
    item.innerHTML = `<div class="d-flex justify-content-between gap-3 align-items-start">
        <div>
          <div class="fw-semibold">${escapeHtml(d.title)}</div>
          <div class="small text-muted">${escapeHtml(d.kind)} • ${escapeHtml(d.file_name || d.link_url || "")}</div>
          ${d.file_size ? `<div class="small text-muted">${formatBytes(d.file_size)}</div>` : ""}
        </div>
        <div class="small d-flex gap-2 align-items-center">
          ${linkHtml}
          <button class="btn btn-sm btn-outline-danger" onclick="deleteDoc(${projectId}, ${d.id})">Delete</button>
        </div>
      </div>`;
    list.appendChild(item);
  }
}

async function addDoc(projectId) {
  const title = document.getElementById("docTitle").value.trim() || "Document";
  const link = document.getElementById("docLink").value.trim();
  const file = document.getElementById("docFile").files[0];
  const msg = document.getElementById("docMsg");
  msg.className = "small mt-2";
  msg.textContent = "Adding...";

  if (file) {
    const form = new FormData();
    form.append("title", title);
    form.append("file", file);
    const res = await api(`/api/docs/projects/${projectId}/docs`, {
      method: "POST",
      headers: authHeaders(),
      body: form
    });
    msg.classList.add(res.ok ? "text-success" : "text-danger");
    msg.textContent = res.ok ? "Uploaded!" : (res.data?.error || "Upload failed");
    if (res.ok) {
      document.getElementById("docTitle").value = "";
      document.getElementById("docLink").value = "";
      document.getElementById("docFile").value = "";
      await Promise.all([loadDocs(projectId), loadMetrics(projectId), loadDashboardSummary()]);
    }
    return;
  }

  if (link) {
    const res = await api(`/api/docs/projects/${projectId}/docs`, {
      method: "POST",
      headers: { ...authHeaders({ "Content-Type": "application/json" }) },
      body: JSON.stringify({ title, link_url: link })
    });
    msg.classList.add(res.ok ? "text-success" : "text-danger");
    msg.textContent = res.ok ? "Link added!" : (res.data?.error || "Failed");
    if (res.ok) {
      document.getElementById("docTitle").value = "";
      document.getElementById("docLink").value = "";
      await Promise.all([loadDocs(projectId), loadMetrics(projectId), loadDashboardSummary()]);
    }
    return;
  }

  msg.classList.add("text-danger");
  msg.textContent = "Choose a file or enter a link.";
}

async function deleteDoc(projectId, docId) {
  const res = await api(`/api/docs/docs/${docId}`, {
    method: "DELETE",
    headers: authHeaders()
  });
  const msg = document.getElementById("docMsg");
  msg.className = `small mt-2 ${res.ok ? "text-success" : "text-danger"}`;
  msg.textContent = res.ok ? "Document deleted." : (res.data?.error || "Delete failed");
  if (res.ok) await Promise.all([loadDocs(projectId), loadMetrics(projectId), loadDashboardSummary()]);
}

async function loadMetrics(projectId) {
  const box = document.getElementById("metricsBox");
  if (!box) return;
  box.textContent = "Loading metrics...";
  const res = await api(`/api/analytics/projects/${projectId}/metrics`, { headers: authHeaders() });
  if (!res.ok) {
    box.innerHTML = `<span class="text-danger">${res.data?.error || "Failed"}</span>`;
    return;
  }
  const m = res.data;
  const dueSoon = (m.due_soon || []).slice(0, 3).map(item =>
    `<div class="small ${deadlineClass(item.days_until_due)}">${escapeHtml(item.title)} • ${escapeHtml(item.due_date || "")}</div>`
  ).join("") || '<div class="small text-muted">No upcoming due dates.</div>';
  box.innerHTML = `
    <div class="d-flex justify-content-between"><span><b>Progress</b></span><span>${m.progress_percent}%</span></div>
    <div class="progress my-2"><div class="progress-bar" role="progressbar" style="width:${m.progress_percent}%"></div></div>
    <div class="mt-1"><b>Tasks</b>: ${m.tasks.total} total</div>
    <div class="ms-3">TODO: ${m.tasks.todo}</div>
    <div class="ms-3">IN_PROGRESS: ${m.tasks.in_progress}</div>
    <div class="ms-3">DONE: ${m.tasks.done}</div>
    <div class="ms-3 text-danger">Overdue: ${m.tasks.overdue}</div>
    <div class="mt-2"><b>Documents</b>: ${m.documents.count}</div>
    <div class="mt-3"><b>Closest Deadlines</b></div>
    ${dueSoon}
  `;
}

function deadlineLabel(days) {
  if (days == null) return "No due date";
  if (days < 0) return `${Math.abs(days)} day(s) overdue`;
  if (days === 0) return "Due today";
  if (days === 1) return "Due tomorrow";
  return `Due in ${days} days`;
}
function deadlineClass(days) {
  if (days == null) return "text-muted";
  if (days < 0) return "text-danger fw-semibold";
  if (days <= 2) return "text-warning fw-semibold";
  return "text-muted";
}
function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}
function formatDateTime(value) {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}
function formatBytes(value) {
  if (!value && value !== 0) return "";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function escapeAttr(s) { return escapeHtml(s).replace(/"/g, "&quot;"); }

document.addEventListener("DOMContentLoaded", () => {
  showLogoutIfToken();
  if (window.location.pathname === "/projects") loadProjects();
  if (window.location.pathname === "/dashboard") loadDashboardSummary();
  if (window.PROJECT_ID) loadProjectAll(window.PROJECT_ID);
});
