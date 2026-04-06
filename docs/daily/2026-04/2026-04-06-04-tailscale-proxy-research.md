# Tailscale Sidecar Proxy 連線研究

## 核心發現

Cloud Run 上的 Tailscale sidecar 使用 userspace networking（因為 Cloud Run 不提供 `/dev/net/tun`），對外連線透過 SOCKS5 proxy。

- SOCKS5 proxy 位置：`localhost:1055`
- app 需要設定 `ALL_PROXY=socks5://localhost:1055/` 來透過 tailnet 連線
- 官方文件：https://tailscale.com/docs/install/cloud/cloudrun

## 官方文件的做法（舊版，單一 container）

官方範例是在同一個 container 裡跑 `tailscaled` + app：

```bash
#!/bin/sh
/app/tailscaled --tun=userspace-networking --socks5-server=localhost:1055 &
/app/tailscale up --auth-key=${TAILSCALE_AUTHKEY} --hostname=cloudrun-app
echo Tailscale started
ALL_PROXY=socks5://localhost:1055/ /app/my-app
```

## 我們的做法（multi-container sidecar）

用 Cloud Run 的 multi-container 功能，Tailscale 跑在獨立的 sidecar container。
因為 multi-container 共用 network namespace，app container 一樣可以用 `localhost:1055` 連到 Tailscale 的 SOCKS5 proxy。

## PostgreSQL 連線的挑戰

PostgreSQL 用 TCP 連線，不是 HTTP。Python 的 `psycopg2` 不直接支援 SOCKS5 proxy。

可能的解法：
1. `PySocks` — monkey-patch socket 層，讓所有 TCP 連線走 SOCKS5
2. `asyncpg` + `python-socks` — asyncpg 本身不支援 proxy，需要額外處理
3. 環境變數 `ALL_PROXY` — 只對支援 proxy 的 library 有效，psycopg2 不認這個

最簡單的做法可能是用 `PySocks` 在 app 啟動時 monkey-patch socket：

```python
import socks
import socket
socks.set_default_proxy(socks.SOCKS5, "localhost", 1055)
socket.socket = socks.socksocket
```

這樣所有 TCP 連線（包含 psycopg2）都會自動走 SOCKS5 proxy。

## Reflection

- 情境：需要從 Cloud Run 的 app container 透過 Tailscale 連到本機 PostgreSQL。決策：研究 SOCKS5 proxy 方式。為什麼：Cloud Run 不提供 TUN device，Tailscale 只能用 userspace networking，對外連線只能透過 SOCKS5 proxy（localhost:1055）。
- 情境：psycopg2 不支援 SOCKS5 proxy。決策：考慮用 PySocks monkey-patch socket 層。為什麼：這是最簡單的做法，不需要換 database driver，一行設定就能讓所有 TCP 連線走 proxy。
