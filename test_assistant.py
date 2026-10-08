import unittest
from assistant import SQLAssistant
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
        self.assertEqual(schema['users'], ['id', 'name'])

    def test_sql_validation_success(self):
        is_valid, _ = self.assistant.validate_sql("SELECT name FROM users")
        self.assertTrue(is_valid)

    def test_malicious_query(self):
        is_valid, _ = self.assistant.validate_sql("DROP TABLE users")
        self.assertFalse(is_valid)

if __name__ == '__main__':
    unittest.main()
