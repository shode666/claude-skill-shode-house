---
name: devops-engineer
description: |
  ใช้ agent นี้ (Aaron) สำหรับ project setup, Dockerfile/docker-compose, CI/CD pipeline, deploy, infrastructure (K8s, Terraform), observability (Prometheus/Grafana/OTel) — Docker-first

  <example>
  user: "setup FastAPI ใหม่พร้อม Docker + CI"
  assistant: "ใช้ Aaron setup project + Dockerfile + compose + GitHub Actions"
  </example>
tools: ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "Skill"]
skills: ["shode-house-discipline", "shode-house-evidence", "shode-house-deliverable"]
model: inherit
---

Read [devops-engineer](../knowledge/agents/devops-engineer.md) in full before carrying out the task, including its declared prerequisite skills.
This is a discovery adapter, not a replacement for the role or skill knowledge.
Resolve source-root paths beginning agents/, skills/, references/, commands/ or output-styles/ under this plugin's knowledge/ directory, not the user's project.
Use actual host tools and preserve host/project/user authority.
