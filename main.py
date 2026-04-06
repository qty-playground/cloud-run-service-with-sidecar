import os

import socks
import socket
import psycopg2
from fastapi import FastAPI

app = FastAPI()

DB_HOST = os.environ.get("DB_HOST", "100.80.130.36")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_USER = os.environ.get("DB_USER", "demo")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "demo-cloud-run-2026")
DB_NAME = os.environ.get("DB_NAME", "demo")
SOCKS5_HOST = os.environ.get("SOCKS5_HOST", "localhost")
SOCKS5_PORT = int(os.environ.get("SOCKS5_PORT", "1055"))

# Enable SOCKS5 proxy for all socket connections (Tailscale userspace networking)
if os.environ.get("ENABLE_SOCKS5_PROXY", "false").lower() == "true":
    socks.set_default_proxy(socks.SOCKS5, SOCKS5_HOST, SOCKS5_PORT)
    socket.socket = socks.socksocket


@app.get("/")
def root():
    return {"message": "Hello, Cloud Run!"}


@app.get("/db")
def db_check():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME,
    )
    cur = conn.cursor()
    cur.execute("SELECT version()")
    version = cur.fetchone()[0]
    cur.close()
    conn.close()
    return {"pg_version": version}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
