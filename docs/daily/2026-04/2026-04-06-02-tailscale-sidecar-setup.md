# Tailscale Sidecar 設定過程

## GCP Secret Manager

- 啟用 API：`gcloud services enable secretmanager.googleapis.com`
- 建立 secret：`echo -n "tskey-auth-xxxxx" | gcloud secrets create tailscale-auth-key --data-file=-`
- 授權 Cloud Run service account 讀取：
  ```
  gcloud secrets add-iam-policy-binding tailscale-auth-key \
    --member="serviceAccount:464419571270-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
  ```
- 費用：前 6 個版本免費、前 10,000 次存取免費，demo 場景基本不產生費用
- 刪除方式：`gcloud secrets delete tailscale-auth-key`

## Tailscale Auth Key 設定

- 位置：https://login.tailscale.com/admin/settings/keys
- Description: `gcp-cloud-run-demo`
- Reusable: ON（多個 Cloud Run instance 共用同一把 key）
- Ephemeral: ON（instance 回收後自動從 tailnet 移除）
- Expiration: 56 天
- Tags: OFF
- 截圖：[tailscale-generate-auth-key.png](../images/tailscale-generate-auth-key.png)

## Knative YAML 重點

- `run.googleapis.com/container-dependencies`：Tailscale 先啟動，app 才啟動
- `TS_USERSPACE: "true"`：Cloud Run 不支援 TUN device，必須用 userspace networking
- `TS_STATE_DIR`：搭配 emptyDir volume，instance 回收後清除，冷啟動需重新認證
- `TS_AUTHKEY`：透過 GCP Secret Manager secretKeyRef 注入
- Billing：request-based（cpu-throttling: true），適合「處理請求時才透過 Tailscale 連出去」的場景
- Scaling：min 0 / max 1

## 本機 PostgreSQL 連線資訊（for demo）

- Tailscale IP: 100.80.130.36
- Port: 5432
- User: demo
- Password: demo-cloud-run-2026
- Database: demo

## Reflection

- 情境：Tailscale auth key 有 Reusable 和 Ephemeral 兩個選項。決策：兩個都開。為什麼：Reusable 讓多個 Cloud Run instance 能用同一把 key；Ephemeral 讓 instance 回收後自動從 tailnet 移除，避免累積離線節點。
- 情境：billing 模式要選 request-based 或 instance-based。決策：選 request-based。為什麼：使用場景是處理請求時才透過 Tailscale 連出去存取 DB，不需要 tailnet 主動連入，不需要 Tailscale daemon 持續運行。
- 情境：Tailscale auth key 到期天數預設 90 天。決策：使用者改成 56 天。為什麼：demo 用途，不需要太長的有效期。
