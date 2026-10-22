# Execution boundaries and remaining risks

## Database permissions and operations

The browser database is a temporary file opened through SQLite `mode=ro`. Application validation rejects empty, multiple, oversized and non-SELECT statements plus write/control keywords, but sqlparse is not a proof of SQL safety. During browser query execution a SQLite authorizer independently permits only read-related operations and the displayed `customers` / `orders` tables. It refuses writes, attachment, PRAGMA actions, hidden schema access and extension/file/blob functions. The authorizer is reset when execution ends; schema introspection runs outside that execution guard.

Tests bypass `validate_sql` deliberately and still observe refusal at the database boundary. A normal SELECT succeeds after failures, exercising cleanup. This is evidence for the covered SQLite operations, not certification against all SQL vulnerabilities.

## Resource controls

Queries have a one-second progress-handler deadline, a 100-row return cap and a 1 MiB SQLite value-size limit. The latter covers single values, not total resident process memory. Expensive recursive work is interrupted; allocation can still occur between progress callbacks. The database contains four fictional customers and four orders, keeping available data small.

Model output is limited to 1600 tokens and the SQL character limit. Browser generation has a ten-second configured timeout, no SDK retries, and a semaphore allowing two concurrent model requests. These are per-request/concurrency bounds, not a global provider-spend quota.

## External generation is explicit

Default mode sends no provider requests. `SQL_LLM_ENABLED=true` plus a configured random `SQL_GENERATION_TOKEN` of at least 32 characters enables `/api/generate` using operator-provided credentials, model and optional compatible endpoint. The generation endpoint requires an exact, constant-time token comparison in `X-SQL-Generation-Token` before taking a model slot or contacting a provider. Wrong/missing tokens return 401. No configured token means generation stays disabled. The browser password field is cleared after the request and the application does not use persistent browser storage for it. Metadata never includes the token. Use TLS outside localhost. Questions and schema are transmitted to that endpoint. API clients cannot supply their own database or provider URLs. A generated preview never executes in this endpoint; the user must submit a separate execution request. Guided questions remain predefined and provider-free.

A shared operator token gates generation, but the service has no user-account authentication, user isolation or monetary budget. Provider-enabled mode belongs on a trusted local/private service until those controls are added. Do not distribute the shared token broadly or put a paid key behind an unrestricted public deployment. Browser provider failures expose the exception class, not raw provider text, URLs or credentials.

## Other database dialects

The library retains SQLAlchemy dialect support and dialect-specific SQL prompts. PostgreSQL connection options include statement timeout; MySQL requires external execution-time controls. SQLite authorizer/value-size controls do not apply to PostgreSQL or MySQL. Neither was integration-tested in this rebuild. Provision dedicated read-only roles before using a real database.

## Prompt injection and correctness

The prompt asks for read-only SQL, but safety does not depend on obedience. A model can still misunderstand a question, hallucinate columns, produce refused SQL or return a semantically wrong SELECT. The system prompt and SQL preview are not prompt-injection solutions. Structural guards contain covered operations; deterministic evaluation measures answer rows on explicit fixtures. No live-model accuracy, business savings or superiority over external projects has been measured.
