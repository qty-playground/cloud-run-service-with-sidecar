# TCP Port Forwarding via SOCKS5 Proxy - 工具比較

## 需求

將 localhost:15432 透過 SOCKS5 proxy (localhost:1055) 轉發到 remote:5432。

## 工具比較表

| 工具 | GitHub Stars | 最近更新 | 安裝難度 | 支援 TCP→SOCKS5 轉發 | 備註 |
|------|-------------|----------|----------|---------------------|------|
| gost v2 (ginuerzh/gost) | 17,795 | 2024-12 (維護中但不再活躍開發) | Go binary, ~10MB | 原生支援 | v2 已進入維護模式 |
| gost v3 (go-gost/gost) | 6,586 | 2025-11 | Go binary, ~15MB | 原生支援 | v3 是活躍開發版本 |
| 3proxy | 5,046 | 2026-04 (活躍) | C 編譯, ~200KB | 支援 (tcppm + parent proxy) | 需要寫設定檔 |
| microsocks | 2,055 | 2025-02 | C 編譯, ~20KB | 不支援 (僅是 SOCKS5 server) | 不適用此場景 |
| proxychains-ng | 10,550 | 2026-01 | C 編譯, preload lib | 間接支援 (wrap 任意程式) | 需搭配其他工具 |
| chisel | 15,844 | 2026-04 (活躍) | Go binary, ~12MB | 不直接支援 SOCKS5 proxy chain | 主要用途是 HTTP tunnel |

## 結論

microsocks 和 chisel 不適用於此場景 — microsocks 只是 SOCKS5 server，chisel 是建立自己的 tunnel 而非利用既有 SOCKS5 proxy。

最適合的工具是 gost，原生支援且指令簡潔。
