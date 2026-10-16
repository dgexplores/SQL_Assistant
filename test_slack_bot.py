import unittest

from slack_bot import format_rows, strip_mention


class TestSlackBot(unittest.TestCase):
    def test_strip_mention(self):
        self.assertEqual(
            strip_mention("<@U12345> unpaid orders from Berlin?"),
            "unpaid orders from Berlin?")
        self.assertEqual(strip_mention("<@U12345>"), "")

    def test_format_rows_table(self):
        out = format_rows({
            "success": True,
            "rows": [{"name": "Ava", "total": 120.0}],
            "truncated": False,
        })
        self.assertIn("name | total", out)
        self.assertIn("Ava | 120.0", out)

    def test_format_rows_empty(self):
        out = format_rows({"success": True, "rows": [], "truncated": False})
        self.assertEqual(out, "No rows matched.")

    def test_format_rows_error(self):
        out = format_rows({"error": "Unsupported statement type: DROP"})
        self.assertIn("Could not answer that", out)
        self.assertNotIn("Traceback", out)

    def test_format_rows_truncation_noted(self):
        out = format_rows({
            "success": True,
            "rows": [{"a": 1}],
            "truncated": True,
        })
        self.assertIn("first rows only", out)

    def test_format_rows_long_output_cut(self):
        rows = [{"data": "x" * 3000}]
        out = format_rows({"success": True, "rows": rows, "truncated": False})
        self.assertLess(len(out), 3000)
        self.assertIn("too long for Slack", out)


if __name__ == "__main__":
    unittest.main()
