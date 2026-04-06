# 專案初始化與首次部署

## 做了什麼

1. 用 tl-util-init 初始化專案（git, venv, .gitignore, CLAUDE.md）
2. 建立簡單的 FastAPI app + Dockerfile
3. 在 qty-playground org 建立 GitHub repo，用 SSH 作為 remote
4. 透過 twjug-lite-gcp-deploy 部署到 Cloud Run（asia-east1）

## 學到的事

- 本機 PostgreSQL（docker container `screenmax-postgres-dev`）綁 `0.0.0.0:5432`，可透過 Tailscale IP 連線
- Tailscale IPv4: `100.80.130.36`
- PostgreSQL 的 user 不是預設的 `postgres`，而是 `dooh-console`（db: `dooh`）
- 為 demo 建立了獨立的 user/db：`demo` / `demo-cloud-run-2026` / db: `demo`
- `gh repo create` 用 https 建 remote，但 push 需要用 SSH，手動 `git remote set-url` 切換

## 部署結果

- Service URL: https://cloud-run-service-with-sidecar-d6kjq3auoa-de.a.run.app
- Billing: request-based, min 0 / max 1 instance

## Reflection

- 情境：`gh repo create` 建完 repo 後用 https push 失敗。決策：把 remote 改成 SSH。為什麼：使用者指定要用 SSH，且 SSH key 不受 gh token scope 限制，連線較穩定。
- 情境：要測試 Cloud Run 透過 Tailscale 連回本機 DB，需要連線資訊。決策：建立獨立的 `demo` user/db，不直接用既有的 `dooh-console`/`dooh`。為什麼：使用者要求建新 user，也避免 demo 過程影響既有資料。
