import unittest
import os
import tempfile
from unittest import mock
from assistant import SQLAssistant, _clean_sql, _format_schema
from sqlalchemy import create_engine, text

class TestSQLAssistant(unittest.TestCase):
    def setUp(self):
        self.db_url = "sqlite:///:memory:"
        self.assistant = SQLAssistant(self.db_url)
        # Create a dummy table
        with self.assistant.engine.connect() as conn:
            conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"))
            conn.commit()

    def test_schema_introspection(self):
        schema = self.assistant.get_schema()
        self.assertIn('users', schema)
        self.assertEqual(
            [c["name"] for c in schema['users']["columns"]],
            ['id', 'name'])
        self.assertTrue(
            all(c["type"] for c in schema['users']["columns"]))

    def test_schema_includes_foreign_keys(self):
        with self.assistant.engine.connect() as conn:
            conn.execute(text(
                "CREATE TABLE orders (id INTEGER PRIMARY KEY, "
                "user_id INTEGER REFERENCES users(id))"))
            conn.commit()
        schema = self.assistant.get_schema()
        fks = schema["orders"]["foreign_keys"]
        self.assertEqual(len(fks), 1)
        self.assertEqual(fks[0]["referred_table"], "users")
        rendered = _format_schema(schema)
        self.assertIn("users(id:", rendered)
        self.assertIn("orders.user_id -> users.id", rendered)

    def test_sql_validation_success(self):
        is_valid, _ = self.assistant.validate_sql("SELECT name FROM users")
        self.assertTrue(is_valid)

    def test_malicious_query(self):
        is_valid, _ = self.assistant.validate_sql("DROP TABLE users")
        self.assertFalse(is_valid)

    def test_validation_boundaries(self):
        for bad in ["", "   ", "EXPLAIN SELECT 1",
                    "SELECT 1; SELECT 2",
                    "SELECT 1; DROP TABLE users",
                    "DELETE FROM users"]:
            with self.subTest(sql=bad):
                self.assertFalse(self.assistant.validate_sql(bad)[0])

    def test_with_cte_allowed(self):
        is_valid, _ = self.assistant.validate_sql(
            "WITH x AS (SELECT 1 AS n) SELECT * FROM x")
        self.assertTrue(is_valid)

    def test_clean_sql_fences(self):
        self.assertEqual(
            _clean_sql("```sql\nSELECT 1\n```"), "SELECT 1")
        self.assertEqual(
            _clean_sql("```\nSELECT 1\n```"), "SELECT 1")

    def test_max_rows_truncation(self):
        assistant = SQLAssistant(self.db_url, max_rows=2)
        with assistant.engine.connect() as conn:
            conn.execute(text("CREATE TABLE t (id INTEGER)"))
            conn.execute(text("INSERT INTO t VALUES (1), (2), (3)"))
            conn.commit()
        out = assistant.execute_query("SELECT * FROM t ORDER BY id",
                                      retries=0)
        self.assertTrue(out.get("success"))
        self.assertEqual(len(out["rows"]), 2)
        self.assertTrue(out["truncated"])

    def test_oversize_query_rejected(self):
        assistant = SQLAssistant(self.db_url, max_sql_chars=10)
        out = assistant.execute_query("SELECT 123456789", retries=0)
        self.assertIn("error", out)

    def test_data_modifying_cte_rejected(self):
        # sqlparse types these as SELECT at the top level; the token denylist
        # is what actually stops them.
        for sql in [
            "WITH x AS (DELETE FROM users RETURNING *) SELECT * FROM x",
            "WITH x AS (INSERT INTO t VALUES (1)) SELECT * FROM x",
            "WITH x AS (UPDATE users SET name='a') SELECT * FROM x",
        ]:
            with self.subTest(sql=sql):
                is_valid, _ = self.assistant.validate_sql(sql)
                self.assertFalse(is_valid)

    def test_read_only_cte_still_allowed(self):
        for sql in [
            "WITH x AS (SELECT 1 AS n) SELECT * FROM x",
            "WITH RECURSIVE r AS (SELECT 1) SELECT * FROM r",
            "SELECT * FROM users WHERE id IN (SELECT 1)",
        ]:
            with self.subTest(sql=sql):
                is_valid, _ = self.assistant.validate_sql(sql)
                self.assertTrue(is_valid)

    def test_llm_failure_returns_error_shape(self):
        # No API key in test env: LLM path must degrade to {"error": ...}
        os.environ.pop("OPENAI_API_KEY", None)
        out = self.assistant.ask("how many users")
        self.assertIn("error", out)
        self.assertNotIn("rows", out)

    def test_base_url_reaches_compatible_provider(self):
        # base_url must reach the client constructor so non-OpenAI
        # endpoints (OpenRouter, Groq, Ollama, ...) actually get used.
        with mock.patch("assistant.OpenAI") as factory:
            SQLAssistant(self.db_url, base_url="http://localhost:11434/v1").ask("x")
        _, kwargs = factory.call_args
        self.assertEqual(kwargs.get("base_url"), "http://localhost:11434/v1")

    def test_unreachable_provider_returns_error_shape(self):
        # Closed port, no key: transport failure, not an exception.
        os.environ.pop("OPENAI_API_KEY", None)
        assistant = SQLAssistant(self.db_url, base_url="http://127.0.0.1:9/v1",
                                 llm_timeout_s=3)
        out = assistant.ask("how many users")
        self.assertIn("error", out)

    def test_connect_args_per_dialect(self):
        # create_engine is lazy (no connection), so Postgres branching is
        # testable without a live server by observing the factory call.
        cases = [
            ("sqlite:///x.db", 5, {"timeout": 5}),
            ("postgresql://u:p@h/db", 5, {"options": "-c statement_timeout=5000"}),
            ("mysql://u:p@h/db", 5, {}),
        ]
        for url, timeout_s, want in cases:
            with self.subTest(url=url):
                # This test observes dialect options, not event dispatch. Real
                # engines exercise progress handlers in test_web.py.
                with mock.patch("assistant.create_engine") as factory, mock.patch(
                    "assistant.event.listens_for", return_value=lambda fn: fn
                ):
                    SQLAssistant(url, timeout_s=timeout_s)
                _, kwargs = factory.call_args
                self.assertEqual(kwargs["connect_args"], want)

    def test_schema_sees_later_ddl(self):
        # Schema is inspected fresh: tables created after construction appear.
        with tempfile.TemporaryDirectory() as tmp:
            assistant = SQLAssistant(f"sqlite:///{tmp}/t.db")
            with assistant.engine.connect() as conn:
                conn.execute(text("CREATE TABLE t1 (id INTEGER)"))
                conn.commit()
            self.assertIn("t1", assistant.get_schema())
            with assistant.engine.connect() as conn:
                conn.execute(text("CREATE TABLE t2 (id INTEGER)"))
                conn.commit()
            self.assertIn("t2", assistant.get_schema())

if __name__ == '__main__':
    unittest.main()
