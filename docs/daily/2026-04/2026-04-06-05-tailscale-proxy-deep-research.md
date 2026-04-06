# Tailscale Sidecar Proxy 深入研究

延續 04 的研究，更完整地整理 Cloud Run + Tailscale sidecar + PostgreSQL 的連線方式。

## 1. Cloud Run Sidecar 的網路架構

Cloud Run multi-container 的所有 container 共用同一個 network namespace。意思是：
- sidecar 在 port 1055 開 SOCKS5 proxy，app container 可以直接用 `localhost:1055` 存取
- 甚至可以用 container 名稱（如 `tailscale:1055`）來連線
- 不需要額外的 network 設定

## 2. 環境變數整理（containerboot / Docker image）

Tailscale 官方 Docker image 用 `containerboot` 作為 entrypoint，支援以下 proxy 相關環境變數：

| 環境變數 | 說明 | 預設 |
|---|---|---|
| `TS_USERSPACE` | 使用 userspace networking（不需要 TUN device） | `true`（預設開啟） |
| `TS_SOCKS5_SERVER` | SOCKS5 proxy 監聽位址，如 `:1055` | 未設定（不啟動） |
| `TS_OUTBOUND_HTTP_PROXY_LISTEN` | HTTP proxy 監聯位址，如 `:8080` | 未設定（不啟動） |

其中 `TS_SOCKS5_SERVER` 等同於 `tailscaled --socks5-server=`，
`TS_OUTBOUND_HTTP_PROXY_LISTEN` 等同於 `tailscaled --outbound-http-proxy-listen=`。

注意：`TS_OUTBOUND_HTTP_PROXY_LISTEN` 只處理 HTTP/HTTPS 流量，PostgreSQL 等 TCP 流量無法使用。

## 3. TS_USERSPACE=false 在 Cloud Run 上不可行

Cloud Run 不提供 `/dev/net/tun` device，所以 `TS_USERSPACE=false`（kernel networking）無法使用。
這也是為什麼必須用 SOCKS5 proxy 的原因 — userspace networking 模式下，Tailscale 不會建立虛擬網路介面，
應用程式無法直接連到 tailnet IP，只能透過 proxy。

## 4. PostgreSQL 連線方案比較

### 方案 A：PySocks monkey-patch（最簡單）

```python
import socks
import socket
socks.set_default_proxy(socks.SOCKS5, "localhost", 1055)
socket.socket = socks.socksocket
```

優點：一行搞定，psycopg2 不需要任何修改
缺點：所有 socket 連線都會走 SOCKS5，可能影響其他連線（如 health check）

### 方案 B：socat 本地 port forwarding

在 app container 裡跑 socat，把本地的 5432 port forward 到 tailnet 上的 PostgreSQL：

```bash
socat TCP-LISTEN:5432,fork,reuseaddr SOCKS5:localhost:TAILNET_PG_IP:5432,socks5port=1055
```

優點：app 只要連 `localhost:5432`，完全不需要改程式碼
缺點：需要安裝 socat，且 socat 的 SOCKS5 支援需要特定版本

### 方案 C：gost (GO Simple Tunnel) port forwarding

```bash
gost -L tcp://:5432 -F socks5://localhost:1055 -F tcp://TAILNET_PG_IP:5432
```

優點：單一 binary，支援 SOCKS5 chain
缺點：需要額外安裝 gost

### 方案 D：Tailscale pgproxy

Tailscale 有出一個專門的 PostgreSQL proxy（`pgproxy`），使用 tsnet library 直接加入 tailnet。
但它的設計目的是 TLS-enforcing proxy，主要用在 server side，不太適合 Cloud Run sidecar 情境。

## 5. 推薦做法

對我們的 FastAPI + psycopg2 場景，推薦方案 A（PySocks monkey-patch），理由：
- 最少的額外依賴（只需要 `PySocks` package）
- 不需要改 Dockerfile（不用裝 socat 或 gost）
- 程式碼改動最小

如果擔心 monkey-patch 影響其他連線，可以只在建立 DB 連線時使用 SOCKS5 socket，
而不是全域 monkey-patch。

## 參考資料

- Tailscale 官方 Cloud Run 文件：https://tailscale.com/kb/1108/cloudrun
- Userspace networking 說明：https://tailscale.com/docs/concepts/userspace-networking
- Docker 環境變數參數：https://tailscale.com/docs/features/containers/docker/docker-params
- containerboot 原始碼：https://pkg.go.dev/tailscale.com/cmd/containerboot
- psycopg2 proxy issue：https://github.com/psycopg/psycopg2/issues/1117
- asyncpg SOCKS5 issue：https://github.com/MagicStack/asyncpg/issues/1136
- Tailscale port forwarding FR：https://github.com/tailscale/tailscale/issues/15345
