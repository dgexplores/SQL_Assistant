# SQL Assistant Security & Tradeoffs

## Why `sqlparse` + Read-Only DB User is Safer than Prompting

Using an LLM to generate SQL directly against an unrestricted database is a security risk (prompt injection/malicious queries). This SQL Assistant employs a security-in-depth approach:

1.  **Static Analysis via `sqlparse`**: Before execution, we parse the generated SQL to ensure it is only a `SELECT` statement. This prevents `DROP`, `DELETE`, `UPDATE`, or other destructive commands from reaching the database engine.
2.  **Principle of Least Privilege**: Even with `sqlparse`, the database engine should be configured with a **read-only user**. If a malicious query bypasses the parsing layer, the database engine level security will reject the destructive command, providing a second layer of defense.
3.  **Self-Correction**: The assistant now automatically reflects on `sqlalchemy.exc.SQLAlchemyError` to refine generated SQL, improving reliability while maintaining the same validation constraints.
