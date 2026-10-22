"""Separate executor correctness from optional, real model generation quality."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant import SQLAssistant

DATASET = Path(__file__).with_name("benchmark.json")


def equivalent(actual, expected):
    """Compare row multisets, preserving column positions and duplicate rows.

    Alias names may differ. Values may not migrate between columns, and strings
    stay strings. Small floating-point roundoff is tolerated, not rounded-away
    money errors. Row ordering is unspecified by these questions.
    """
    if len(actual) != len(expected):
        return False
    remaining = [list(row) for row in expected]
    for row in actual:
        values = list(row.values()) if isinstance(row, dict) else list(row)
        match = next((i for i, candidate in enumerate(remaining)
                      if len(values) == len(candidate) and all(
                          math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-6)
                          if isinstance(a, (int, float)) and isinstance(b, (int, float))
                          else type(a) is type(b) and a == b
                          for a, b in zip(values, candidate))), None)
        if match is None:
            return False
        remaining.pop(match)
    return True


def run(mode="reference", dataset_path=DATASET):
    raw = Path(dataset_path).read_bytes()
    dataset = json.loads(raw)
    report = {
        "dataset": dataset["version"], "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "mode": mode, "created_at": datetime.now(timezone.utc).isoformat(),
        "model": os.getenv("EVAL_MODEL", "gpt-4o-mini") if mode == "live" else None,
        "measures": "NL-to-SQL execution accuracy" if mode == "live" else "reference-SQL executor correctness; NOT model accuracy",
        "limitations": dataset["description"], "cases": [],
    }
    if mode == "live" and not os.getenv("OPENAI_API_KEY"):
        return {**report, "status": "not_run", "reason": "OPENAI_API_KEY is missing; no model requests made"}
    with tempfile.TemporaryDirectory(prefix="sql-eval-") as folder:
        path = Path(folder) / "evaluation.db"
        with sqlite3.connect(path) as conn:
            for statement in dataset["seed"]:
                conn.execute(statement)
        assistant = SQLAssistant(
            f"sqlite:///file:{path}?mode=ro&uri=true", max_rows=1000, timeout_s=2,
            model=report["model"] or "unused", base_url=os.getenv("OPENAI_BASE_URL"),
            llm_timeout_s=float(os.getenv("EVAL_LLM_TIMEOUT", "30")),
            sqlite_read_guard=True, allowed_tables=set(),
        )
        for case in dataset["cases"]:
            started = time.perf_counter()
            # Live mode receives only the question/schema, never gold SQL/rows.
            result = assistant.ask(case["question"]) if mode == "live" else assistant.execute_query(case["reference_sql"], retries=0)
            passed = bool(result.get("success") and not result.get("truncated") and equivalent(result["rows"], case["expected"]))
            report["cases"].append({
                "id": case["id"], "category": case["category"], "difficulty": case["difficulty"],
                "passed": passed, "elapsed_ms": round((time.perf_counter()-started)*1000, 2),
                "actual": result.get("rows"), "error": result.get("error"),
                "executed_sql": result.get("sql"),
            })
        assistant.engine.dispose()
    grouped = defaultdict(lambda: Counter(total=0, passed=0))
    for case in report["cases"]:
        grouped[case["difficulty"]]["total"] += 1
        grouped[case["difficulty"]]["passed"] += case["passed"]
    report.update(status="completed", total=len(report["cases"]), passed=sum(c["passed"] for c in report["cases"]), by_difficulty=dict(grouped))
    report["accuracy"] = report["passed"] / report["total"]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["reference", "live"], default="reference")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    args = parser.parse_args()
    report = run(args.mode, args.dataset)
    serialized = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized)
    print(serialized)
    return 2 if report["status"] == "not_run" else int(report["passed"] != report["total"])


if __name__ == "__main__":
    raise SystemExit(main())
