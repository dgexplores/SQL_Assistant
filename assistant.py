import sqlalchemy
from sqlalchemy import create_engine, inspect, exc
import sqlparse
import os
from openai import OpenAI


def _get_client():
    # Lazy init so `import assistant` works without a key (tests, schema-only use).
    # Raises a clear error only when an LLM call is actually attempted.
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _clean_sql(sql):
    sql = (sql or "").strip()
    # Handle ```sql ... ``` and generic ``` ... ``` fences
    if sql.startswith("```"):
        lines = sql.splitlines()
        lines = lines[1:]  # drop opening fence
        # drop closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        sql = "\n".join(lines).strip()
        # bare trailing fence without newline
        if sql.endswith("```"):
            sql = sql[:-3].strip()
    return sql

class SQLAssistant:
    def __init__(self, db_url, max_rows=1000, timeout_s=30, max_sql_chars=20000):
        self.max_rows = max_rows
        self.timeout_s = timeout_s
        self.max_sql_chars = max_sql_chars
        # SQLite supports a busy/wait timeout via connect_args; other dialects
        # need dialect-specific statement timeouts (future work, documented).
        if db_url.startswith("sqlite"):
            self.engine = create_engine(
                db_url, connect_args={"timeout": timeout_s}
            )
        else:
            self.engine = create_engine(db_url)
        self.inspector = inspect(self.engine)

    def get_schema(self):
        schema = {}
        for table_name in self.inspector.get_table_names():
            columns = self.inspector.get_columns(table_name)
            schema[table_name] = [col['name'] for col in columns]
        return schema

    def validate_sql(self, sql):
        if not sql or not sql.strip():
            return False, "Empty query"
        statements = [s for s in sqlparse.parse(sql) if str(s).strip()]
        if len(statements) != 1:
            return False, "Only single-statement queries are allowed"
        stmt = statements[0]
        stmt_type = stmt.get_type()
        # sqlparse reports WITH ... SELECT as UNKNOWN; allow read-only CTEs explicitly.
        if stmt_type == 'UNKNOWN' and str(stmt).lstrip().upper().startswith('WITH'):
            return True, "Valid"
        if stmt_type != 'SELECT':
            return False, f"Unsupported statement type: {stmt_type}"
        return True, "Valid"

    def execute_query(self, sql, retries=1):
        if sql and len(sql) > self.max_sql_chars:
            return {"error": f"Query exceeds {self.max_sql_chars} characters"}
        valid, msg = self.validate_sql(sql)
        if not valid:
            return {"error": msg}
        with self.engine.connect() as conn:
            try:
                result = conn.execute(sqlalchemy.text(sql))
                # Fetch one extra row to detect truncation without LIMIT rewriting.
                raw = result.fetchmany(self.max_rows + 1)
                truncated = len(raw) > self.max_rows
                rows = [dict(r._mapping) for r in raw[:self.max_rows]]
                return {"success": True, "rows": rows, "truncated": truncated}
            except exc.SQLAlchemyError as e:
                if retries > 0:
                    return self.ask_for_correction(sql, str(e), retries - 1)
                return {"error": str(e)}
            except Exception as e:
                return {"error": str(e)}

    def ask_for_correction(self, original_sql, error, retries):
        prompt = f"The SQL query generated was: {original_sql}. It resulted in the following error: {error}. Please provide a corrected SQL query that fixes the error. Only return the SQL string."
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        sql = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
        return self.execute_query(_clean_sql(sql), retries=retries)

    def ask(self, question):
        if question and len(question) > self.max_sql_chars:
            return {"error": f"Question exceeds {self.max_sql_chars} characters"}
        schema = self.get_schema()
        prompt = f"Given this schema: {schema}, generate a valid SQL query to answer: {question}. Only return the SQL string."
        
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        sql = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
        return self.execute_query(_clean_sql(sql))
