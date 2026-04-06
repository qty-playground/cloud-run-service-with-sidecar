import os
import traceback

import psycopg2
from fastapi import FastAPI

app = FastAPI()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_USER = os.environ.get("DB_USER", "demo")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "demo-cloud-run-2026")
DB_NAME = os.environ.get("DB_NAME", "demo")


@app.get("/")
def root():
    return {"message": "Hello, Cloud Run!"}


@app.get("/db")
def db_check():
    try:
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
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
