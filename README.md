# Automated Engineering Project Management Dashboard (Microservices Starter)

This is a working microservices starter for an **Automated Engineering Project Management Dashboard** built with Flask, Postgres, Docker Compose, and a Bootstrap web UI.

## Services
- **api-gateway** — single entry point that proxies all service APIs
- **auth-service** — register/login + JWT
- **project-service** — projects, members, and GitHub repo metadata
- **task-service** — task CRUD with due dates and statuses
- **docs-service** — document metadata + file uploads
- **git-service** — GitHub recent commits integration
- **analytics-service** — project metrics + dashboard summary
- **web-ui** — login, dashboard overview, project management pages

## What is new in this version
- Added a polished **Dashboard** overview page
- Added **portfolio-level analytics** across all projects
- Added **GitHub repo field** for each project
- Added **recent commits panel** on the project page
- Kept the task/document management improvements from the prior version

## Quick start
1. Install Docker Desktop
2. From the project root, run:
```bash
docker compose up --build
```
3. Open the UI at:
- http://localhost:3000

## Suggested demo flow
1. Register and log in
2. Open the **Dashboard** page
3. Create a project from **Projects**
4. Add a GitHub repo like `octocat/Hello-World`
5. Add a few tasks with different statuses and due dates
6. Upload a document or add a link
7. Return to the Dashboard and show updated metrics, overdue counts, and upcoming deadlines
8. Open the project page and show recent GitHub commits

## Notes
- This is designed as a class-project scaffold, not a production deployment.
- GitHub API calls work without a token for public repositories, but rate limits are lower.
- Postgres volumes will persist data between runs unless you remove Docker volumes.
