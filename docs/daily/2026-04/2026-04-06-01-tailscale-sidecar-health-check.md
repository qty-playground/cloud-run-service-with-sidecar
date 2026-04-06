# Tailscale Sidecar Health Check on Cloud Run

## 問題

原本的 knative service.yaml 使用 `tcpSocket` startup probe 對 port 41112 做健康檢查，但一直失敗。

## 發現

### Port 41112 不是 Tailscale 的 health check port

查遍 Tailscale 官方文件，沒有任何地方提到 port 41112。這個 port 號沒有根據。

### 正確的 Health Check 設定

Tailscale 從 1.72 版開始提供 `/healthz` HTTP endpoint，在 1.78 版後改用以下環境變數：

- `TS_ENABLE_HEALTH_CHECK=true`：啟用 `/healthz` endpoint
- `TS_LOCAL_ADDR_PORT`：指定監聽位址與 port，預設為 `[::]:9002`

`/healthz` endpoint 行為：
- 當節點取得至少一個 tailnet IP 時回傳 `200 OK`
- 否則回傳 `503`

舊的 `TS_HEALTHCHECK_ADDR_PORT` 已在 1.78 版 deprecated。

### 建議的 startup probe 設定

```yaml
env:
  - name: TS_ENABLE_HEALTH_CHECK
    value: "true"
startupProbe:
  httpGet:
    path: /healthz
    port: 9002
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 6
```

使用 httpGet 而非 tcpSocket，因為 Tailscale 提供的是 HTTP endpoint。

## 來源

- [Tailscale on Google Cloud Run](https://tailscale.com/kb/1108/cloudrun)
- [Docker configuration parameters](https://tailscale.com/docs/features/containers/docker/docker-params)
- [FR: Docker Container Healthcheck - Issue #12758](https://github.com/tailscale/tailscale/issues/12758)
