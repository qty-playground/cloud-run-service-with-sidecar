#!/bin/sh

# socat: forward localhost:15432 → tailnet PostgreSQL via SOCKS5 proxy
socat TCP-LISTEN:15432,fork,reuseaddr SOCKS4A:localhost:${DB_HOST}:${DB_PORT},socksport=1055 &

# start app
exec python main.py
