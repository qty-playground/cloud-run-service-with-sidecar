import os

import psycopg2
from fastapi import FastAPI

app = FastAPI()

DB_USER = os.environ.get("DB_USER", "demo")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "demo-cloud-run-2026")
DB_NAME = os.environ.get("DB_NAME", "demo")


@app.get("/")
def root():
    return {"message": "Hello, Cloud Run!"}


@app.get("/db")
def db_check():
    conn = psycopg2.connect(
        host="localhost",
        port=15432,
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
