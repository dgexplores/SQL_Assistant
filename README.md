# SQL_Assistant

Natural-language → SQL over any SQLAlchemy database, with a validation layer
that refuses to run anything but read-only queries.

## What it does

`SQLAssistant.ask("how many users signed up last week?")` introspects the live
schema, asks `gpt-4o-mini` for SQL, validates it, and executes it. If the query
errors, it feeds the error back for one self-correction attempt.

```python
from assistant import SQLAssistant

assistant = SQLAssistant("sqlite:///app.db")
assistant.ask("top 5 customers by order total")
```

## The Number

Every failure mode was measured against `sqlparse`, not assumed:

| Input | Result |
| --- | --- |
| `DROP` / `DELETE` / `CREATE` | rejected |
| `''`, `'   '` (empty query) | rejected |
| `SELECT 1; DROP TABLE users` (multi-statement) | rejected |
| `EXPLAIN SELECT 1` | rejected |
| `WITH x AS (DELETE FROM users RETURNING *) SELECT * FROM x` | rejected |
| `WITH x AS (SELECT 1) SELECT * FROM x` (read-only CTE) | allowed |

The data-modifying CTE row is the one that matters. `sqlparse` types that
statement as `SELECT`, so a top-level type check alone accepts a query that
deletes every row. Token-level keyword inspection is what actually stops it.
11 tests / 12 subtests cover these boundaries, runnable with no API key.

## The Tradeoff

**Chosen: `sqlparse` static validation, not asking the model to behave.**

Telling an LLM "only return SELECT statements" is a prompt, and prompts are not
a security boundary — instruction injection in the question or the schema is
enough to defeat one. Parsing the SQL is deterministic: the same string always
gets the same verdict, and a reviewer's objection to the design is answered by
pointing at code rather than re-running a model.

The cost is honest: `sqlparse` is not a full SQL parser, so the denylist is
conservative. It rejects some dialect-specific read syntax that happens to use a
denied keyword name, and it does **not** replace a read-only database role. Both
guards are needed — see [SECURITY_TRADEOFFS.md](SECURITY_TRADEOFFS.md).

## Architecture

| Layer | Responsibility |
| --- | --- |
| `get_schema()` | Introspect tables → columns for the prompt |
| `validate_sql()` | Reject empty, multi-statement, non-SELECT, write-keyword queries |
| `execute_query()` | Bound input size, execute, cap rows, return one failure shape |
| `_generate_and_run()` | Single LLM call path; converts LLM failures to `{"error": ...}` |

## Configuration

`SQLAssistant(db_url, max_rows=1000, timeout_s=30, max_sql_chars=20000, model="gpt-4o-mini", llm_timeout_s=30)`

- `max_rows` — result cap. Results report `truncated: true` when more rows exist.
- `max_sql_chars` — rejects oversized SQL *and* oversized questions before any DB or LLM call.
- `timeout_s` — SQLite busy timeout. Postgres/MySQL need a dialect-specific `statement_timeout`; not wired yet.
- `model`, `llm_timeout_s` — LLM call bound.

## Contract

Every public method returns a dict, never raises for expected failures:

```python
{"success": True, "rows": [...], "truncated": False}
{"error": "Unsupported statement type: DROP"}
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # add your key
export OPENAI_API_KEY=sk-...
python -m pytest test_assistant.py -v
```

Tests run without an API key — the LLM client is created lazily and only on an
actual LLM call.

## Known limitations

1. `sqlparse` denylist can reject legitimate dialect syntax; tune
   `WRITE_KEYWORDS` for your target databases.
2. `timeout_s` is SQLite-only. Postgres needs `SET statement_timeout`.
3. Schema is truncated to column names — no types or foreign keys, which costs
   accuracy on joins. Token cost grows linearly with table count.
4. `inspect()` is captured in `__init__`; DDL after construction is invisible.
5. One self-correction attempt, then the raw DB error is returned.