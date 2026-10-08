import sqlalchemy
from sqlalchemy import create_engine, inspect, exc
import sqlparse
import os
from openai import OpenAI

# Initialize LLM client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SQLAssistant:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.inspector = inspect(self.engine)

    def get_schema(self):
        schema = {}
        for table_name in self.inspector.get_table_names():
            columns = self.inspector.get_columns(table_name)
            schema[table_name] = [col['name'] for col in columns]
        return schema

    def validate_sql(self, sql):
        statements = sqlparse.parse(sql)
        for stmt in statements:
            if stmt.get_type() not in ['SELECT', 'UNKNOWN']:
                return False, f"Unsupported statement type: {stmt.get_type()}"
        return True, "Valid"

    def execute_query(self, sql, retries=1):
        valid, msg = self.validate_sql(sql)
        if not valid:
            return {"error": msg}
        with self.engine.connect() as conn:
            try:
                result = conn.execute(sqlalchemy.text(sql))
                rows = result.fetchall()
                return {"success": True, "rows": [dict(r._mapping) for r in rows]}
            except exc.SQLAlchemyError as e:
                if retries > 0:
                    return self.ask_for_correction(sql, str(e), retries - 1)
                return {"error": str(e)}
            except Exception as e:
                return {"error": str(e)}

    def ask_for_correction(self, original_sql, error, retries):
        prompt = f"The SQL query generated was: {original_sql}. It resulted in the following error: {error}. Please provide a corrected SQL query that fixes the error. Only return the SQL string."
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        sql = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
        # Clean markdown code blocks if LLM returns them
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.endswith("```"):
            sql = sql[:-3]
        return self.execute_query(sql.strip(), retries=retries)

    def ask(self, question):
        schema = self.get_schema()
        prompt = f"Given this schema: {schema}, generate a valid SQL query to answer: {question}. Only return the SQL string."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        sql = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
        # Clean markdown code blocks if LLM returns them
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.endswith("```"):
            sql = sql[:-3]
        
        return self.execute_query(sql.strip())
