import time
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import exc

from assistant import SQLAssistant
from web import app


def test_demo_answers_and_database_write_boundary():
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        for path in ("/static/style.css", "/static/app.js", "/docs", "/healthz"):
            assert client.get(path).status_code == 200
        data = client.post("/api/ask", json={"question": "Revenue by region"}).json()
        assert data["rows"] == [{"region": "South", "revenue": 250.0}, {"region": "North", "revenue": 200.0}]
        assert client.post("/api/ask", json={"question": "Customers with no orders"}).json()["rows"] == [{"name": "Rohan"}]
        assert client.post("/api/query", json={"sql": "DELETE FROM customers"}).status_code == 422
        # Bypass the application validator: database permissions still deny writes.
        with app.state.assistant.engine.connect() as connection:
            try:
                connection.exec_driver_sql("DELETE FROM customers")
            except exc.OperationalError:
                pass
            else:
                raise AssertionError("demo database must be read-only")
        assert client.post("/api/ask", json={"question": "invent an answer"}).status_code == 422


def test_expensive_query_is_interrupted():
    assistant = SQLAssistant("sqlite://", timeout_s=0.02)
    started = time.monotonic()
    result = assistant.execute_query("WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<100000000) SELECT SUM(x) FROM n", retries=0)
    assert "error" in result
    assert time.monotonic() - started < 2


def test_connection_outage_has_consistent_error_response():
    assistant = SQLAssistant("sqlite://")
    with patch.object(assistant.engine, "connect", side_effect=exc.OperationalError("connect", {}, Exception("offline"))):
        assert "error" in assistant.execute_query("SELECT 1")
        assert "error" in assistant.ask("count rows")
