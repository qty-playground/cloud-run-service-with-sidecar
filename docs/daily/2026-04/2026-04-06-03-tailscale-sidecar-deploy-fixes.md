# Tailscale Sidecar 部署踩坑紀錄

## 問題 1：ghcr.io image 不被 Cloud Run 接受

Cloud Run 只接受以下 registry 的 image：
- `[region.]gcr.io`
- `[region-]docker.pkg.dev`
- `docker.io`

原本用 `ghcr.io/tailscale/tailscale:latest` 會報錯：
> Expected an image path like [host/]repo-path[:tag and/or @digest], where host is one of [region.]gcr.io, [region-]docker.pkg.dev or docker.io

解法：改用 `docker.io/tailscale/tailscale:latest`。

如果一定要用其他 registry 的 image，需要建立 Artifact Registry remote repository 來代理。

## 問題 2：Tailscale startup probe port 錯誤

原本 template 用 `tcpSocket` port 41112，這個 port 沒有根據，導致 startup probe 失敗：
> The user-provided container failed the configured startup probe checks.

正確做法：
- 加環境變數 `TS_ENABLE_HEALTH_CHECK=true`（Tailscale v1.78+ 支援）
- 改用 `httpGet` probe，path `/healthz`，port `9002`
- `/healthz` 回傳 200 代表節點已取得 tailnet IP，503 代表尚未就緒

參考來源：
- https://tailscale.com/kb/1108/cloudrun
- https://tailscale.com/docs/features/containers/docker/docker-params
- https://github.com/tailscale/tailscale/issues/12758

## 問題 3：Secret Manager API 未啟用

建立 secret 前需要先啟用 API：
```
gcloud services enable secretmanager.googleapis.com
```

## 部署結果

第三次部署成功，service 正常回應。

| 嘗試 | 問題 | 解法 |
|------|------|------|
| 第 1 次 | ghcr.io 不被接受 | 改用 docker.io |
| 第 2 次 | startup probe port 41112 錯誤 | 改用 /healthz port 9002 + TS_ENABLE_HEALTH_CHECK |
| 第 3 次 | 成功 | - |

## Reflection

- 情境：Cloud Run 不接受 ghcr.io 的 image。決策：改用 docker.io 的同一個 image。為什麼：最簡單的修法，Tailscale 同時發布到 Docker Hub 和 ghcr.io，功能完全相同。另一個選項是建 Artifact Registry remote repository 來代理 ghcr.io，但 demo 場景不值得這個複雜度。
- 情境：Tailscale startup probe 失敗。決策：用 /healthz endpoint port 9002 取代 tcpSocket port 41112。為什麼：port 41112 沒有官方根據，Tailscale 從 v1.78 起提供 /healthz HTTP endpoint（需要 TS_ENABLE_HEALTH_CHECK=true），這才是正確的健康檢查方式。
