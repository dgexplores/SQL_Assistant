"""End-to-end accuracy smoke test for SQL Assistant.

Seeds a tiny SQLite DB, asks each dataset question through SQLAssistant.ask(),
and compares returned rows to the gold answers. Needs OPENAI_API_KEY; without
one it prints SKIP and exits 0 (CI never runs this).

Comparison is order-insensitive on both rows and columns: each row becomes a
sorted tuple of stringified values. This tolerates SELECT * vs explicit column
lists and missing ORDER BY, but it is still a smoke signal, not a benchmark:
a semantically right answer with extra columns fails, and five toy questions
prove nothing about real schemas. Run: python eval/run_eval.py
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text

from assistant import SQLAssistant


def normalize(rows):
    return sorted(tuple(sorted(str(v) for v in r.values())) for r in rows)


def expected_rows(case):
    return sorted(tuple(sorted(str(v) for v in row)) for row in case["expected"])


def main():
    # Any OpenAI-compatible provider works: set OPENAI_API_KEY plus
    # OPENAI_BASE_URL (and EVAL_MODEL to override the default model).
    # Local Ollama example (no real key needed):
    #   ollama serve & ollama pull qwen2.5-coder:1.5b
    #   OPENAI_API_KEY=ollama OPENAI_BASE_URL=http://localhost:11434/v1 \
    #     EVAL_MODEL=qwen2.5-coder:1.5b python eval/run_eval.py
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("OPENAI_BASE_URL"):
        print("SKIP: set OPENAI_API_KEY (or OPENAI_BASE_URL for a compatible endpoint); eval needs a live model call.")
        return 0
    model = os.getenv("EVAL_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL")
    with open(os.path.join(os.path.dirname(__file__), "dataset.json")) as f:
        dataset = json.load(f)
    passed = 0
    for case in dataset["cases"]:
        with tempfile.TemporaryDirectory() as tmp:
            db_url = f"sqlite:///{tmp}/eval.db"
            engine = create_engine(db_url)
            with engine.connect() as conn:
                for stmt in dataset["seed"]:
                    conn.execute(text(stmt))
                conn.commit()
            engine.dispose()
            out = SQLAssistant(db_url, model=model, base_url=base_url).ask(case["question"])
        ok = out.get("success") and normalize(out["rows"]) == expected_rows(case)
        passed += bool(ok)
        got = out.get("rows", out.get("error"))
        print(f"{'PASS' if ok else 'FAIL'} {case['id']}: got {got}")
    print(f"{passed}/{len(dataset['cases'])} correct")
    return 0 if passed == len(dataset["cases"]) else 1


if __name__ == "__main__":
    sys.exit(main())
