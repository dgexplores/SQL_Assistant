"""Public, synthetic-data SQL playground. Never accepts a database URL."""
from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3
import os
import hmac
import threading
import tempfile
import time

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from assistant import SQLAssistant

ROOT = Path(__file__).resolve().parent
EXAMPLES = [
    {"question": "Revenue by region", "sql": "SELECT c.region, SUM(o.amount) AS revenue FROM customers c JOIN orders o ON c.id=o.customer_id GROUP BY c.region ORDER BY revenue DESC"},
    {"question": "Customers with no orders", "sql": "SELECT c.name FROM customers c LEFT JOIN orders o ON c.id=o.customer_id WHERE o.id IS NULL ORDER BY c.name"},
    {"question": "Monthly revenue", "sql": "SELECT substr(ordered_at,1,7) AS month, SUM(amount) AS revenue FROM orders GROUP BY month ORDER BY month"},
    {"question": "Average order value", "sql": "SELECT ROUND(AVG(amount),2) AS average_order_value FROM orders"},
    {"question": "Orders above 100", "sql": "SELECT id, amount FROM orders WHERE amount > 100 ORDER BY amount DESC, id"},
    {"question": "Customers missing an email", "sql": "SELECT name FROM customers WHERE email IS NULL ORDER BY name"},
]


def seed_database(path: Path):
    with sqlite3.connect(path) as conn:
        conn.executescript("""
        CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, region TEXT, email TEXT);
        CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id), amount REAL, ordered_at TEXT);
        INSERT INTO customers VALUES(1,'Asha','South','asha@example.test'),(2,'Kabir','North',NULL),(3,'Meera','South','meera@example.test'),(4,'Rohan','West',NULL);
        INSERT INTO orders VALUES(1,1,120,'2026-01-02'),(2,1,80,'2026-02-01'),(3,2,200,'2026-01-10'),(4,3,50,'2026-02-04');
        """)


@asynccontextmanager
async def lifespan(application):
    with tempfile.TemporaryDirectory(prefix="sql-showcase-") as folder:
        path = Path(folder) / "analytics.db"
        seed_database(path)
        # SQLite URI read-only mode is the enforcement boundary. The SQL
        # validator is defence in depth, never the database permission model.
        assistant = SQLAssistant(
            f"sqlite:///file:{path}?mode=ro&uri=true", max_rows=100, timeout_s=1,
            sqlite_read_guard=True, allowed_tables={"customers", "orders"},
            model=os.getenv("SQL_LLM_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("OPENAI_BASE_URL"), llm_timeout_s=10,
        )
        application.state.generation_token = os.getenv("SQL_GENERATION_TOKEN", "").strip()
        requested = os.getenv("SQL_LLM_ENABLED", "false").lower() == "true"
        application.state.llm_enabled = requested and len(application.state.generation_token) >= 32
        application.state.generation_slots = threading.BoundedSemaphore(2)
        application.state.assistant = assistant
        yield
        assistant.engine.dispose()


app = FastAPI(title="SQL Assistant · Analytics Lab", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


class Query(BaseModel):
    sql: str = Field(min_length=1, max_length=6000)


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/healthz")
def health():
    return {"status": "ok", "mode": "synthetic-read-only", "llm_enabled": app.state.llm_enabled, "generation_requires_review": True}


@app.get("/api/schema")
def schema():
    return {"schema": app.state.assistant.get_schema(), "examples": EXAMPLES,
            "llm_enabled": app.state.llm_enabled,
            "model": app.state.assistant.model if app.state.llm_enabled else None}


@app.post("/api/query")
def query(payload: Query):
    started = time.perf_counter()
    result = app.state.assistant.execute_query(payload.sql, retries=0)
    if "error" in result:
        # Avoid exposing database paths/driver internals on the public surface.
        raise HTTPException(422, "Query refused or could not run. Use one SELECT statement over the displayed schema; execution is limited to one second.")
    return {**result, "sql": payload.sql, "elapsed_ms": round((time.perf_counter()-started)*1000, 2), "mode": "read-only SQL"}


@app.post("/api/ask")
def ask(payload: Question):
    sample = next((item for item in EXAMPLES if item["question"].casefold() == payload.question.strip().casefold()), None)
    if sample is None:
        raise HTTPException(422, "This hosted demo uses guided questions, without an LLM. Choose an example or edit its SQL. Model-based generation is available through the Python library with your own provider key.")
    return {**query(Query(sql=sample["sql"])), "mode": "guided question · predefined SQL"}


@app.post("/api/generate")
def generate(payload: Question, generation_token: str | None = Header(default=None, alias="X-SQL-Generation-Token", max_length=1024)):
    """Request a provider-generated preview; execution is a separate action."""
    if not app.state.llm_enabled:
        raise HTTPException(503, "Model generation is disabled. Use guided questions or SQL; configure SQL_LLM_ENABLED, SQL_LLM_MODEL, a SQL_GENERATION_TOKEN of at least 32 characters and provider credentials to enable your own questions.")
    if not generation_token or not hmac.compare_digest(
        generation_token.encode("utf-8"), app.state.generation_token.encode("utf-8")
    ):
        raise HTTPException(401, "A valid operator generation token is required.")
    if not app.state.generation_slots.acquire(blocking=False):
        raise HTTPException(429, "Two generation requests are already running. Try again shortly.")
    started = time.perf_counter()
    try:
        result = app.state.assistant.generate_sql(payload.question)
    finally:
        app.state.generation_slots.release()
    if "error" in result:
        raise HTTPException(502, result["error"])
    return {**result, "mode": "model-generated preview · not executed", "elapsed_ms": round((time.perf_counter()-started)*1000, 2)}
