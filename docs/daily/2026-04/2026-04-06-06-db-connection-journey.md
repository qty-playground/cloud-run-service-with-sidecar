# DB 連線方案的試誤過程

從 Cloud Run 透過 Tailscale sidecar 連到本機 PostgreSQL，經歷了多次失敗才找到可行方案。

## 嘗試 1：socat + SOCKS4A

socat 只支援 SOCKS4/SOCKS4A，不支援 SOCKS5。Tailscale 的 proxy 是 SOCKS5，所以 socat 轉發失敗。

## 嘗試 2：PySocks monkey-patch

用 `socks.set_default_proxy()` + `socket.socket = socks.socksocket` 做全域 monkey-patch。

結果：SOCKS5 proxy 本身能通（debug endpoint 驗證 raw socket 連線成功），但 psycopg2 仍然 connection timed out。

原因：psycopg2 底層用 C extension（libpq）管理 socket，不經過 Python 的 `socket.socket`，monkey-patch 無效。

## 嘗試 3：TS_TAILNET_TARGET_IP

想讓 Tailscale 直接把流量轉發到目標 tailnet IP，app 只要連 localhost 就好。

結果：`TS_TAILNET_TARGET_IP is not supported with TS_USERSPACE`

原因：這個功能需要 kernel networking（TUN device），Cloud Run 不提供。

## 成功方案：gost

用 gost（Go Simple Tunnel）做 TCP port forwarding through SOCKS5：

```bash
gost -L "tcp://:15432/${DB_TAILNET_HOST}:${DB_TAILNET_PORT}" -F socks5://localhost:1055
```

App 連 `localhost:15432`，gost 透過 SOCKS5 proxy 轉到 tailnet 上的 PostgreSQL。

gost v2 (ginuerzh/gost)：17,795 stars，單一 Go binary ~10MB，一行指令搞定。

## 最終架構

```
Cloud Run app → gost (localhost:15432) → Tailscale SOCKS5 (:1055) → VPN → 本機 PG :5432
```

## Reflection

- 情境：socat 無法連到 Tailscale 的 SOCKS5 proxy。決策：不再嘗試 socat，改用其他方案。為什麼：socat 只支援 SOCKS4/4A，這是 socat 的限制，無法繞過。
- 情境：PySocks monkey-patch 對 psycopg2 無效。決策：放棄 Python 層的 proxy 方案。為什麼：psycopg2 用 C extension（libpq）管理 socket，不走 Python socket 層。這個限制也適用於大部分用 C binding 的 database driver。
- 情境：TS_TAILNET_TARGET_IP 不支援 userspace 模式。決策：回到 SOCKS5 proxy 路線，用 gost 做 TCP 轉發。為什麼：Cloud Run 不提供 TUN device，只能用 userspace networking，而 TS_TAILNET_TARGET_IP 需要 kernel networking。
- 情境：需要選一個 TCP forwarding through SOCKS5 的工具。決策：選 gost v2。為什麼：stars 最高（17.8k），單一 binary 不需要額外依賴，一行指令搞定，不需要設定檔。
