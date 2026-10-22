# Organization onboarding

This checklist is for the person who operates the database and the person who
operates the assistant. Complete it before connecting a production database.

## 1. Define the data boundary

- Name the database, environment, tables, and user groups the assistant may
  serve.
- Classify the exposed data. Do not connect the assistant to tables containing
  secrets, credentials, or regulated personal data unless the organization has
  approved that access.
- Start with a reporting replica or analytics warehouse, not the primary
  transactional database.

## 2. Create a read-only database identity

The SQL validator is an additional guard; it is **not** a substitute for
database permissions. Use a dedicated identity that has `SELECT` only on the
approved schema or views. Do not grant schema modification, user management,
or access to unrelated schemas.

For PostgreSQL, a typical starting point is:

```sql
CREATE ROLE sql_assistant LOGIN PASSWORD 'use-a-secret-manager';
GRANT CONNECT ON DATABASE analytics TO sql_assistant;
GRANT USAGE ON SCHEMA reporting TO sql_assistant;
GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO sql_assistant;
ALTER DEFAULT PRIVILEGES IN SCHEMA reporting
  GRANT SELECT ON TABLES TO sql_assistant;
```

Adapt this with the database owner; do not run it blindly. Prefer curated views
when row- or column-level restrictions are required.

## 3. Configure the service

```bash
python -m venv .venv
source .venv/bin/activate
pip install '.[slack]'
cp .env.example .env
```

Store the values from `.env` in the organization's secret manager. Never
commit `.env`, database URLs, Slack tokens, or API keys. Set `DB_URL` to the
dedicated read-only identity and run the bot with a process manager or
container platform that injects secrets at runtime.

## 4. Verify before inviting users

1. Run `python -m pytest -v`.
2. Test three representative read-only questions against a non-production
   dataset.
3. Confirm that `DROP TABLE ...` and a data-modifying CTE are rejected.
4. Confirm the database account cannot write even if a query bypasses the
   application validator.
5. Set an owner for the Slack app, database credential rotation, incident
   response, and access reviews.

## 5. Operate safely

- Keep `max_rows`, query timeouts, and model timeouts conservative.
- Review database and Slack access when teams or data classifications change.
- Rotate provider, Slack, and database credentials on the organization's
  normal schedule and immediately after suspected exposure.
- Treat model output as untrusted. The application validates SQL, but only
  database privileges enforce the final access boundary.

See [SECURITY_TRADEOFFS.md](SECURITY_TRADEOFFS.md) for the validator's exact
guarantees and limits.
