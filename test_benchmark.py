from eval.benchmark import equivalent, run


def test_reference_queries_agree_with_handwritten_expected_results():
    report = run()
    assert report["total"] == 18
    assert report["passed"] == 18
    assert report["model"] is None


def test_comparison_preserves_column_identity_duplicates_and_types():
    assert equivalent([{"name": "A", "total": 3}], [["A", 3]])
    assert not equivalent([{"name": 3, "total": "A"}], [["A", 3]])
    assert not equivalent([{"x": 1}], [[1], [1]])
    assert not equivalent([{"x": "3"}], [[3]])
    assert equivalent([{"x": 3.000000001}], [[3]])


def test_unconfigured_live_evaluation_is_not_reported_as_passed(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    report = run("live")
    assert report["status"] == "not_run"
    assert "accuracy" not in report


def test_separate_support_domain_reference_fixtures():
    from pathlib import Path
    report = run(dataset_path=Path(__file__).parent / "eval" / "heldout-support.json")
    assert report["total"] == 12
    assert report["passed"] == 12
    assert report["model"] is None
    assert all(case["executed_sql"] for case in report["cases"])
