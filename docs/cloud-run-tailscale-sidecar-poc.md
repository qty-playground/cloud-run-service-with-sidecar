# Cloud Run + Tailscale Sidecar POC

從 Cloud Run 透過 Tailscale sidecar 連到 tailnet 上的 PostgreSQL。

## 架構

```
Client → Cloud Run (FastAPI :8080)
                ↓
           gost (localhost:15432)
                ↓
         Tailscale SOCKS5 proxy (:1055)
                ↓
            VPN tunnel
                ↓
         本機 PostgreSQL :5432
```

Cloud Run multi-container 的所有 container 共用 network namespace，app 可以直接用 `localhost:1055` 存取 sidecar 開的 SOCKS5 proxy。

但 Cloud Run 不提供 `/dev/net/tun`，Tailscale 只能用 userspace networking，app 無法直接連 tailnet IP，必須透過 SOCKS5 proxy。而 psycopg2 底層用 libpq（C extension）管理 socket，Python 層的 SOCKS5 monkey-patch 無效，所以用 gost 在本地做 TCP port forwarding。

## 關鍵設定

### Knative Service（`knative/service.yaml`）

兩個 container，透過 `container-dependencies` 確保 Tailscale 先啟動：

```yaml
annotations:
  run.googleapis.com/container-dependencies: '{"my-app":["tailscale"]}'
```

Tailscale sidecar 的環境變數：

```yaml
- name: TS_AUTHKEY
  valueFrom:
    secretKeyRef:
      name: tailscale-auth-key
      key: latest
- name: TS_STATE_DIR
  value: /var/lib/tailscale
- name: TS_USERSPACE
  value: "true"
- name: TS_SOCKS5_SERVER
  value: ":1055"
- name: TS_ENABLE_HEALTH_CHECK
  value: "true"
```

Health check 用 `/healthz:9002`（Tailscale v1.78+ 支援，需要 `TS_ENABLE_HEALTH_CHECK=true`）：

```yaml
startupProbe:
  httpGet:
    path: /healthz
    port: 9002
```

Tailscale state 用 memory-backed emptyDir：

```yaml
volumes:
  - name: tailscale-state
    emptyDir:
      medium: Memory
      sizeLimit: 64Mi
```

### Dockerfile

安裝 gost v2 做 TCP port forwarding：

```dockerfile
FROM python:3.12-slim

ADD https://github.com/ginuerzh/gost/releases/download/v2.12.0/gost_2.12.0_linux_amd64.tar.gz /tmp/gost.tar.gz
RUN tar -xzf /tmp/gost.tar.gz -C /usr/local/bin/ gost && rm /tmp/gost.tar.gz
```

### 啟動腳本（`start.sh`）

gost 在背景把 `localhost:15432` 透過 SOCKS5 轉到 tailnet 上的 PostgreSQL，然後啟動 app：

```sh
#!/bin/sh
gost -L "tcp://:15432/${DB_TAILNET_HOST}:${DB_TAILNET_PORT}" -F socks5://localhost:1055 &
exec python main.py
```

App 只要連 `localhost:15432` 就好，不需要知道 proxy 的存在。

### Auth Key

Tailscale auth key 存在 GCP Secret Manager，部署前建立：

```bash
gcloud services enable secretmanager.googleapis.com
echo -n "tskey-auth-..." | gcloud secrets create tailscale-auth-key --data-file=-
```

## 注意事項

- Cloud Run image 只接受 `docker.io`、`gcr.io`、`docker.pkg.dev`，不接受 `ghcr.io`。Tailscale image 用 `docker.io/tailscale/tailscale:latest`。
- `TS_TAILNET_TARGET_IP` 不支援 userspace 模式（`TS_TAILNET_TARGET_IP is not supported with TS_USERSPACE`），別走這條路。
