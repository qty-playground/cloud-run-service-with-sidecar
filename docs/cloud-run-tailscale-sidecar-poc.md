# Cloud Run + Tailscale Sidecar 可行性驗證

Cloud Run 是個方便做概念型 side project 的 serverless 部署環境，但狀態保存需要自己處理。通常會用 GCP 上的 DB 服務或 Supabase 之類的 DBaaS，但如果家裡有簡易的 DB 環境，能不能讓雲端服務直接連回地端？

這個可行性驗證的目標：透過 Tailscale sidecar 讓 Cloud Run 上的服務連到 tailnet 上的本機 PostgreSQL，服務開在雲端，狀態存在地端。

## 最初的想法

1. Cloud Run service 搭一個 Tailscale sidecar
2. 透過 Tailscale 連回 local DB

想像中知道可行，但具體怎麼做？研究之後才發現 Cloud Run 的限制讓事情沒那麼直覺。

## 為什麼需要繞路

Tailscale 一般透過 TUN device（`/dev/net/tun`）建立虛擬網路介面，讓應用程式直接用 tailnet IP 連線，就像在同一個區域網路裡一樣。但 TUN device 需要較高的系統權限，Cloud Run 的 container 環境不提供它。

沒有 TUN device，Tailscale 改用 userspace networking 模式，不建立虛擬網路介面，而是開一個 SOCKS5 proxy 讓應用程式透過它存取 tailnet。

## 實際架構

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

Cloud Run multi-container 的所有 container 共用同一個 network namespace。對開發者來說，這表示它們就像跑在同一台機器上，彼此可以透過 `localhost` 互相存取。所以 app 可以直接用 `localhost:1055` 連到 sidecar 開的 SOCKS5 proxy。

但 psycopg2 不支援 SOCKS proxy，需要一個 TCP port forwarder 把本地 port 透過 SOCKS5 轉到遠端。能做這件事的工具不少，這裡用的是 gost，讓 app 連 `localhost:15432` 就能透通到 tailnet 上的 PostgreSQL。

## 專案結構

```
.
├── main.py                  # FastAPI app
├── start.sh                 # 啟動腳本（gost + app）
├── Dockerfile
├── requirements.txt
├── knative/
│   └── service.yaml         # Cloud Run service 定義（含 sidecar）
└── mini-deployment.yaml     # 部署設定
```

## 範例設定內容

### Knative Service（`knative/service.yaml`）

兩個 container，透過 `container-dependencies` 確保 Tailscale 先啟動：

```yaml
annotations:
  run.googleapis.com/container-dependencies: '{"my-app":["tailscale"]}'
```

Tailscale sidecar container 的完整設定：

```yaml
- name: tailscale
  image: docker.io/tailscale/tailscale:latest
  env:
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
  resources:
    limits:
      cpu: "0.5"
      memory: 256Mi
  volumeMounts:
    - name: tailscale-state
      mountPath: /var/lib/tailscale
  startupProbe:
    httpGet:
      path: /healthz
      port: 9002
    initialDelaySeconds: 5
    periodSeconds: 5
    failureThreshold: 6
```

- `TS_USERSPACE=true`：使用 userspace networking，Cloud Run 唯一可用的模式
- `TS_SOCKS5_SERVER=:1055`：開 SOCKS5 proxy 供 app 使用
- `TS_ENABLE_HEALTH_CHECK=true`：啟用 `/healthz` endpoint（port 9002），供 startup probe 使用（Tailscale v1.78+）
- `TS_AUTHKEY`：從 GCP Secret Manager 注入
- Tailscale state 用 memory-backed emptyDir（`medium: Memory`）

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

## 驗證

部署後用 messages API 驗證整條路徑是否通：

```bash
# 留言
curl -X POST https://<service-url>/messages \
  -H "Content-Type: application/json" \
  -d '{"author": "test", "content": "hello from cloud run"}'

# 列出留言
curl https://<service-url>/messages
```

能成功寫入和讀取，代表 Cloud Run → gost → Tailscale SOCKS5 → VPN → 本機 PostgreSQL 整條路都通了。

