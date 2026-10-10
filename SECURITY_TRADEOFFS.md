# SQL Assistant Security & Tradeoffs

## Why `sqlparse` + Read-Only DB User is Safer than Prompting

Using an LLM to generate SQL directly against an unrestricted database is a
security risk. This assistant uses defence in depth rather than asking the model
to behave.

### Layer 1 — Static analysis (`validate_sql`)

Before execution every query must pass all of:

1. **Non-empty** — `""` and `"   "` are rejected, not executed as a no-op.
2. **Single statement** — `sqlparse` must yield exactly one statement, so
   `SELECT 1; DROP TABLE users` cannot smuggle a second command past the check.
3. **Read-only type** — top-level type must be `SELECT`, or `UNKNOWN` beginning
   with `WITH` (sqlparse does not classify CTEs).
4. **No write keywords anywhere** — a token walk rejects `INSERT`, `UPDATE`,
   `DELETE`, `MERGE`, `UPSERT`, `REPLACE`, `DROP`, `CREATE`, `ALTER`,
   `TRUNCATE`, `GRANT`, `REVOKE`, `VACUUM`.

Rule 4 is not redundant with rule 3. Postgres data-modifying CTEs are typed
`SELECT` by `sqlparse`:

```sql
WITH gone AS (DELETE FROM users RETURNING *) SELECT * FROM gone;
```

A top-level type check alone accepts this and deletes every row. Only the token
walk catches it. Both rules are covered by
`test_data_modifying_cte_rejected`.

### Layer 2 — Least privilege (your responsibility)

The validator is a filter, not a guarantee. `sqlparse` is not a full SQL
parser, and dialects add syntax it does not model. **The database user must be
read-only** (`GRANT SELECT` only). This is the layer that still holds when the
parser does not understand a statement.

### Layer 3 — Resource bounds

Untrusted LLM output must not be able to exhaust memory or time:

- `max_sql_chars` rejects oversized SQL and questions before any DB or LLM call.
- `max_rows` caps rows returned (`fetchmany(max_rows + 1)`, reports `truncated`).
- `llm_timeout_s` bounds the OpenAI call.
- `timeout_s` sets the SQLite busy timeout.

### Layer 4 — Self-correction stays inside the same rules

`ask_for_correction` re-enters `execute_query`, so a corrected query is
validated exactly like the original. A retry cannot bypass the checks, and
`retries` decrements so the loop terminates.

## Prompt injection is not solved here

The question text reaches the LLM, and the schema comes from the database. This
project does not attempt instruction-injection defences on either. The
mitigation is structural: whatever the model is convinced to emit, it still has
to pass validation and the database role. Treat this as a defence-in-depth
measure, not as a complete answer to prompt injection.