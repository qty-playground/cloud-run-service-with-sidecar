#!/bin/sh

# gost: forward localhost:15432 → tailnet PostgreSQL via SOCKS5 proxy
gost -L "tcp://:15432/${DB_TAILNET_HOST}:${DB_TAILNET_PORT}" -F socks5://localhost:1055 &

# start app
exec python main.py
