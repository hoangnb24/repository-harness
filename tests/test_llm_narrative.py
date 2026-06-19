import json
import csv

import pytest
import typer

from vsf_profiler.cli import _llm_provider_from_config, run_pipeline
from vsf_profiler.demo_data import create_small_demo
from vsf_profiler.llm_narrative import (
    OpenAINarrativeProvider,
    build_guardrail_evidence,
    build_narrative_context,
    validate_narrative,
)


class CapturingProvider:
    name = "fake"

    def __init__(self) -> None:
        self.context = {}

    def generate(self, context: dict) -> str:
        self.context = context
        summary = context["summary"]
        issue = context["top_issues"][0]
        column_ref = f"{issue['table']}.{issue['columns'][0]}"
        return (
            "# Data Scientist EDA Narrative\n\n"
            f"The deterministic artifacts show {summary['table_count']} tables, "
            f"{summary['issue_count']} issues, and risk score {summary['risk_score']}.\n\n"
            f"`{issue['issue_type']}` is present on `{column_ref}`.\n\n"
            "Influence findings are association-only and require schema and data owner review.\n"
        )


class BadProvider:
    name = "fake"

    def generate(self, context: dict) -> str:
        return (
            "# Data Scientist EDA Narrative\n\n"
            "The dataset has 999 issues. `ghost_table.bad_column` causes downstream churn.\n"
        )


class DraftEchoOpenAIProvider:
    name = "openai"
    model = "gpt-test"

    def __init__(self) -> None:
        self.context = {}

    def config_summary(self) -> dict:
        return {
            "provider": self.name,
            "model": self.model,
            "external_api": True,
        }

    def generate(self, context: dict) -> str:
        self.context = context
        return context["guardrail_safe_draft"]


def test_fake_provider_writes_l4_report_and_passed_guardrail(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    out_dir = tmp_path / "outputs" / "demo_small"
    provider = CapturingProvider()

    run_pipeline(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
        target="order_reviews.review_score",
        out_dir=out_dir,
        use_llm=True,
        llm_provider=provider,
    )

    guardrail_report = json.loads((out_dir / "guardrail_report.json").read_text())
    l4_report = (out_dir / "l4_report.md").read_text()
    run_summary = json.loads((out_dir / "run_summary.json").read_text())
    report_md = (out_dir / "report.md").read_text()
    report_html = (out_dir / "report.html").read_text()

    assert guardrail_report["status"] == "passed"
    assert guardrail_report["provider"] == "fake"
    assert guardrail_report["model"] == ""
    assert guardrail_report["model_config"]["provider"] == "fake"
    assert guardrail_report["raw_csv_included"] is False
    assert guardrail_report["unbounded_samples_included"] is False
    assert guardrail_report["checked_numbers"]
    assert guardrail_report["checked_refs"]
    assert guardrail_report["violation_count"] == 0
    assert guardrail_report["violations"] == []
    assert "Data Scientist EDA Narrative" in l4_report
    assert "association-only" in l4_report
    assert "l4_report.md" in report_md
    assert "guardrail_report.json" in report_md
    assert "l4_report.md" in report_html
    assert run_summary["artifact_paths"]["l4_report"] == "l4_report.md"
    assert run_summary["artifact_paths"]["guardrail_report"] == "guardrail_report.json"
    assert "llm_narrative" in [stage["name"] for stage in run_summary["stage_timings"]]
    assert provider.context["privacy_contract"] == {
        "raw_csv_included": False,
        "sample_rows_included": False,
        "sample_paths_may_be_referenced": True,
    }
    assert provider.context["source_artifacts"] == [
        "profile_summary.json",
        "issues.json",
        "schema_evaluation.json",
        "relationship_graph.json",
        "dataset_verdict.json",
        "table_assessments.json",
        "charts/*.json",
        "influence.json",
    ]
    assert "guardrail_safe_draft" in provider.context
    assert "Deterministic fallback narrative" not in provider.context["guardrail_safe_draft"]
    assert provider.context["guardrail_contract"]["required_output"] == (
        "Return guardrail_safe_draft exactly as Markdown."
    )
    context_text = json.dumps(provider.context, sort_keys=True)
    for csv_path in sorted((data_dir / "csv").glob("*.csv")):
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for row in reader:
                raw_line = ",".join(row)
                assert raw_line not in context_text


def test_configured_fake_provider_output_passes_guardrail(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    out_dir = tmp_path / "outputs" / "demo_small"
    provider = _llm_provider_from_config("fake")

    run_pipeline(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
        target="order_reviews.review_score",
        out_dir=out_dir,
        use_llm=True,
        llm_provider=provider,
    )

    guardrail_report = json.loads((out_dir / "guardrail_report.json").read_text())
    profile_summary = json.loads((out_dir / "profile_summary.json").read_text())
    l4_report = (out_dir / "l4_report.md").read_text()
    report_md = (out_dir / "report.md").read_text()
    report_html = (out_dir / "report.html").read_text()
    column_count = sum(table["column_count"] for table in profile_summary["tables"].values())

    assert guardrail_report["status"] == "passed"
    assert guardrail_report["provider"] == "fake"
    assert guardrail_report["model"] == "deterministic-fake"
    assert guardrail_report["model_config"]["model"] == "deterministic-fake"
    assert guardrail_report["model_config"]["external_api"] is False
    assert guardrail_report["fallback_reason"] == ""
    assert guardrail_report["violation_count"] == 0
    assert guardrail_report["violations"] == []
    assert "Deterministic fallback narrative" not in l4_report
    assert "Feature Usability Summary" in l4_report
    assert f"The column review classified {column_count} columns" in l4_report
    assert "Table-by-Table Health Review" in l4_report
    assert "Column Issue Blocks" in l4_report
    assert "Influence findings are association-only" in l4_report
    assert "L4 guardrail status: **passed**" in report_md
    assert "provider=fake" in report_md
    assert "L4 guardrail" in report_html
    assert "passed" in report_html


def test_openai_safe_draft_output_passes_without_fallback(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    out_dir = tmp_path / "outputs" / "demo_small"
    provider = DraftEchoOpenAIProvider()

    run_pipeline(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
        target="order_reviews.review_score",
        out_dir=out_dir,
        use_llm=True,
        llm_provider=provider,
    )

    guardrail_report = json.loads((out_dir / "guardrail_report.json").read_text())
    l4_report = (out_dir / "l4_report.md").read_text()
    report_md = (out_dir / "report.md").read_text()

    assert guardrail_report["status"] == "passed"
    assert guardrail_report["provider"] == "openai"
    assert guardrail_report["model"] == "gpt-test"
    assert guardrail_report["fallback_reason"] == ""
    assert guardrail_report["violation_count"] == 0
    assert guardrail_report["violations"] == []
    assert "Guarded provider narrative" in l4_report
    assert "Feature Usability Summary" in l4_report
    assert "Table-by-Table Health Review" in l4_report
    assert "Column Issue Blocks" in l4_report
    assert "Deterministic fallback narrative" not in l4_report
    assert "L4 guardrail status: **passed**" in report_md
    assert "fallback" not in report_md.lower()
    assert provider.context["guardrail_safe_draft"] == l4_report


def test_bad_provider_output_uses_deterministic_fallback(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    out_dir = tmp_path / "outputs" / "demo_small"

    run_pipeline(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
        target="order_reviews.review_score",
        out_dir=out_dir,
        use_llm=True,
        llm_provider=BadProvider(),
    )

    guardrail_report = json.loads((out_dir / "guardrail_report.json").read_text())
    l4_report = (out_dir / "l4_report.md").read_text()
    violation_types = {violation["type"] for violation in guardrail_report["violations"]}

    assert guardrail_report["status"] == "fallback_used"
    assert guardrail_report["fallback_reason"] == "guardrail_failed"
    assert guardrail_report["violation_count"] >= 3
    assert {"numeric_claim", "reference", "causal_wording"}.issubset(violation_types)
    assert "Deterministic fallback narrative" in l4_report
    assert "999" not in l4_report
    assert "ghost_table.bad_column" not in l4_report


def test_missing_provider_config_uses_deterministic_fallback(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    out_dir = tmp_path / "outputs" / "demo_small"

    run_pipeline(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
        target="order_reviews.review_score",
        out_dir=out_dir,
        use_llm=True,
    )

    guardrail_report = json.loads((out_dir / "guardrail_report.json").read_text())
    assert guardrail_report["status"] == "fallback_used"
    assert guardrail_report["fallback_reason"] == "provider_config_missing"
    assert guardrail_report["provider"] == "none"
    assert (out_dir / "l4_report.md").exists()


def test_llm_disabled_preserves_deterministic_artifact_set(tmp_path):
    data_dir = create_small_demo(tmp_path / "data" / "demo_small")
    out_dir = tmp_path / "outputs" / "demo_small"

    run_pipeline(
        dbml_path=data_dir / "schema.dbml",
        csv_dir=data_dir / "csv",
        rules_path=data_dir / "rules.yaml",
        target="order_reviews.review_score",
        out_dir=out_dir,
    )

    run_summary = json.loads((out_dir / "run_summary.json").read_text())
    report_md = (out_dir / "report.md").read_text()
    assert not (out_dir / "l4_report.md").exists()
    assert not (out_dir / "guardrail_report.json").exists()
    assert "l4_report" not in run_summary["artifact_paths"]
    assert "guardrail_report" not in run_summary["artifact_paths"]
    assert "llm_narrative" not in [stage["name"] for stage in run_summary["stage_timings"]]
    assert "Optional L4 EDA Narrative" in report_md
    assert "Optional L4 EDA narrative was not enabled for this deterministic run" in report_md


def test_guardrail_rejects_unsupported_numbers_refs_and_causal_wording():
    artifacts = {
        "profile_summary": {
            "tables": {
                "orders": {
                    "row_count": 2,
                    "column_count": 1,
                    "columns": {"order_id": {"null_count": 0}},
                }
            }
        },
        "issues": [
            {
                "issue_id": "ISSUE-0001",
                "issue_type": "ORPHAN_FOREIGN_KEY",
                "severity": "P1",
                "table": "orders",
                "columns": ["order_id"],
                "bad_count": 1,
            }
        ],
        "schema_evaluation": {"summary": {"mapped_table_count": 1}},
        "relationship_graph": {"summary": {"edge_count": 1}},
        "dataset_verdict": {
            "verdict": "WARN",
            "risk_score": 42,
            "issue_counts": {"by_severity": {"P1": 1}, "by_type": {"ORPHAN_FOREIGN_KEY": 1}},
        },
        "table_assessments": {
            "assessments": [
                {
                    "table": "orders",
                    "role": "fact",
                    "health_score": 42,
                    "readiness": "WARN",
                    "business_impact": {
                        "category": "transaction_event_quality",
                        "label": "Transaction event quality",
                    },
                }
            ]
        },
        "chart_specs": {},
        "influence": {"target": "orders.order_id", "top_features": [], "row_count": 0},
    }
    context = build_narrative_context(artifacts)
    evidence = build_guardrail_evidence(artifacts, context)

    passed = validate_narrative(
        "There are 1 issues on `orders.order_id` with risk score 42.",
        evidence,
    )
    failed = validate_narrative(
        "There are 999 issues on `missing_table.missing_column` and that causes churn.",
        evidence,
    )

    assert passed["status"] == "passed"
    field_ref_passed = validate_narrative(
        "Review the `health_score` and `relationship_risk_count` fields in table_assessments.json.",
        evidence,
    )
    assert field_ref_passed["status"] == "passed"
    assert failed["status"] == "failed"
    assert {violation["type"] for violation in failed["violations"]} == {
        "numeric_claim",
        "reference",
        "causal_wording",
    }


def test_guardrail_rejects_unsupported_business_impact_claims():
    artifacts = {
        "profile_summary": {
            "tables": {
                "orders": {"row_count": 2, "column_count": 1, "columns": {"order_id": {}}},
                "order_reviews": {"row_count": 2, "column_count": 1, "columns": {"review_id": {}}},
            }
        },
        "issues": [],
        "schema_evaluation": {"summary": {"mapped_table_count": 2}},
        "relationship_graph": {"summary": {"edge_count": 0}},
        "dataset_verdict": {
            "verdict": "READY",
            "risk_score": 0,
            "issue_counts": {"by_severity": {}, "by_type": {}},
        },
        "table_assessments": {
            "assessments": [
                {
                    "table": "orders",
                    "role": "fact",
                    "health_score": 100,
                    "readiness": "READY",
                    "business_impact": {
                        "category": "transaction_event_quality",
                        "label": "Transaction event quality",
                    },
                },
                {
                    "table": "order_reviews",
                    "role": "event",
                    "health_score": 100,
                    "readiness": "READY",
                    "business_impact": {
                        "category": "feedback_signal_quality",
                        "label": "Feedback signal quality",
                    },
                },
            ]
        },
        "chart_specs": {},
        "influence": {"target": None, "top_features": [], "row_count": 0},
    }
    context = build_narrative_context(artifacts)
    evidence = build_guardrail_evidence(artifacts, context)

    passed = validate_narrative(
        "`orders` has impact category `transaction_event_quality`.",
        evidence,
    )
    mismatched = validate_narrative(
        "`orders` has impact category `feedback_signal_quality`.",
        evidence,
    )
    unsupported = validate_narrative(
        "`orders` has financial reporting analysis impact.",
        evidence,
    )

    assert passed["status"] == "passed"
    assert mismatched["status"] == "failed"
    assert any(
        violation["type"] == "table_business_impact"
        for violation in mismatched["violations"]
    )
    assert unsupported["status"] == "failed"
    assert any(
        violation["type"] == "business_impact"
        for violation in unsupported["violations"]
    )


def test_openai_provider_uses_responses_api_without_raw_csv_payload():
    calls = []

    def fake_transport(url, headers, payload, timeout_seconds):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        return {
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": "# Data Scientist EDA Narrative\n\n"
                            "The deterministic artifacts show 1 tables and 2 rows.\n\n"
                            "Influence findings are association-only.",
                        }
                    ]
                }
            ]
        }

    provider = OpenAINarrativeProvider(
        api_key="test-key",
        model="gpt-test",
        base_url="https://example.test/v1/",
        timeout_seconds=12.5,
        max_output_tokens=345,
        transport=fake_transport,
    )
    context = {
        "role": "Data Scientist",
        "source_artifacts": ["profile_summary.json", "issues.json"],
        "privacy_contract": {
            "raw_csv_included": False,
            "sample_rows_included": False,
            "sample_paths_may_be_referenced": True,
        },
        "summary": {"table_count": 1, "row_count": 2},
        "tables": [{"table": "orders", "columns": ["order_id"], "row_count": 2}],
        "top_issues": [],
        "guardrail_safe_draft": "# Data Scientist EDA Narrative\n\n"
        "The deterministic artifacts show 1 tables and 2 rows.\n\n"
        "Influence findings are association-only.",
        "guardrail_contract": {
            "required_output": "Return guardrail_safe_draft exactly as Markdown.",
        },
    }

    narrative = provider.generate(context)

    assert "Data Scientist EDA Narrative" in narrative
    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == "https://example.test/v1/responses"
    assert call["headers"]["Authorization"] == "Bearer test-key"
    assert call["headers"]["Content-Type"] == "application/json"
    assert call["timeout_seconds"] == 12.5
    assert call["payload"]["model"] == "gpt-test"
    assert call["payload"]["max_output_tokens"] == 345
    assert provider.config_summary() == {
        "provider": "openai",
        "model": "gpt-test",
        "base_url": "https://example.test/v1",
        "timeout_seconds": 12.5,
        "max_output_tokens": 345,
    }
    assert "raw CSV data" in call["payload"]["instructions"]
    request_payload = json.loads(call["payload"]["input"])
    request_context = request_payload["context"]
    assert request_payload["guardrail_safe_draft"] == context["guardrail_safe_draft"]
    assert request_payload["guardrail_contract"] == context["guardrail_contract"]
    assert "Return that Markdown exactly" in call["payload"]["instructions"]
    assert request_context["privacy_contract"]["raw_csv_included"] is False
    assert request_context["privacy_contract"]["sample_rows_included"] is False
    assert ".csv" not in call["payload"]["input"]
    assert "data/demo_small/csv" not in call["payload"]["input"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"api_key": "test key"}, "API key"),
        ({"model": "bad model"}, "VSF_OPENAI_MODEL"),
        ({"base_url": "https://example.test/v1?debug=true"}, "VSF_OPENAI_BASE_URL"),
        ({"base_url": "http://example.test/v1"}, "VSF_OPENAI_BASE_URL"),
        ({"base_url": "https://example.test/../v1"}, "VSF_OPENAI_BASE_URL"),
        ({"timeout_seconds": 0}, "VSF_OPENAI_TIMEOUT_SECONDS"),
        ({"timeout_seconds": float("nan")}, "VSF_OPENAI_TIMEOUT_SECONDS"),
        ({"max_output_tokens": 999999}, "VSF_OPENAI_MAX_OUTPUT_TOKENS"),
    ],
)
def test_openai_provider_rejects_invalid_model_config(kwargs, message):
    config = {
        "api_key": "test-key",
        "model": "gpt-test",
        "base_url": "https://example.test/v1",
        "timeout_seconds": 12.5,
        "max_output_tokens": 345,
    }
    config.update(kwargs)

    with pytest.raises(ValueError, match=message):
        OpenAINarrativeProvider(**config)


def test_openai_config_without_api_key_falls_back_to_missing_provider(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VSF_PROFILER_LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert _llm_provider_from_config(None) is None


def test_openai_config_rejects_invalid_env_model_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VSF_PROFILER_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("VSF_OPENAI_MODEL", "bad model")

    with pytest.raises(typer.BadParameter, match="Invalid OpenAI L4 provider config"):
        _llm_provider_from_config(None)


def test_openai_config_can_load_env_example_style_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VSF_PROFILER_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("VSF_OPENAI_MODEL", raising=False)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "VSF_PROFILER_LLM_PROVIDER=openai",
                "OPENAI_API_KEY=test-key",
                "VSF_OPENAI_MODEL=gpt-test",
            ]
        ),
        encoding="utf-8",
    )

    provider = _llm_provider_from_config(None)

    assert isinstance(provider, OpenAINarrativeProvider)
    assert provider.model == "gpt-test"
