import os
import traceback
from datetime import datetime, timezone

import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "15432"))
DB_USER = os.environ.get("DB_USER", "demo")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "demo-cloud-run-2026")
DB_NAME = os.environ.get("DB_NAME", "demo")


def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME,
    )


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


class MessageIn(BaseModel):
    author: str
    content: str


@app.on_event("startup")
def startup():
    try:
        init_db()
    except Exception as e:
        print(f"Warning: failed to init db: {e}")


@app.get("/")
def root():
    return {"message": "Hello, Cloud Run!"}


@app.post("/messages")
def leave_message(msg: MessageIn):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (author, content) VALUES (%s, %s) RETURNING id, created_at",
        (msg.author, msg.content),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {"id": row[0], "author": msg.author, "content": msg.content, "created_at": str(row[1])}


@app.get("/messages")
def list_messages():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, author, content, created_at FROM messages ORDER BY created_at DESC LIMIT 50")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "author": r[1], "content": r[2], "created_at": str(r[3])} for r in rows]


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
