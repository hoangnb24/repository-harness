from __future__ import annotations

import csv
import json
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from vsf_profiler.artifact_audit import REQUIRED_CHARTS, audit_artifacts
from vsf_profiler.cli import run_pipeline
from vsf_profiler.connectors import DEFAULT_POSTGRES_CHUNK_ROWS
from vsf_profiler.export_package import create_analysis_package
from vsf_profiler.influence_analyzer import MAX_ANALYSIS_ROWS, MAX_FEATURE_COLUMNS


PERFORMANCE_GUARD_REPORT = "performance_guard_report.json"
GENERATOR_VERSION = 1
DEFAULT_BENCHMARK_ROWS = 5_000
DEFAULT_BENCHMARK_TABLES = 7
DEFAULT_BENCHMARK_SEED = 20260616
DEFAULT_SIGNAL_COLUMNS = 12
MIN_TABLE_COUNT = 5
TABLE_ORDER = [
    "customers",
    "products",
    "sellers",
    "orders",
    "order_reviews",
    "order_payments",
    "order_items",
    "shipments",
    "support_tickets",
    "inventory_events",
]
FETCHDF_TOKEN = "." + "fetchdf("
PANDAS_READ_CSV_TOKEN = "pandas." + "read_csv"
PD_READ_CSV_TOKEN = "pd." + "read_csv"
PANDAS_IMPORT_TOKEN = "import " + "pandas"
FROM_PANDAS_TOKEN = "from " + "pandas"


@dataclass(frozen=True)
class GeneratedBenchmarkDataset:
    root: Path
    dbml_path: Path
    csv_dir: Path
    rules_path: Path
    target: str
    requested_rows: int
    requested_tables: int
    seed: int
    signal_columns: int
    table_rows: dict[str, int]

    @property
    def total_rows(self) -> int:
        return sum(self.table_rows.values())


def create_large_benchmark_dataset(
    *,
    root: Path,
    rows: int,
    tables: int,
    seed: int = DEFAULT_BENCHMARK_SEED,
    signal_columns: int = DEFAULT_SIGNAL_COLUMNS,
    force: bool = False,
) -> GeneratedBenchmarkDataset:
    _validate_generator_args(rows=rows, tables=tables, signal_columns=signal_columns)
    if root.exists():
        if not force:
            raise ValueError(f"Benchmark input directory already exists: {root}")
        shutil.rmtree(root)
    csv_dir = root / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)
    selected_tables = TABLE_ORDER[:tables]
    table_rows = _table_row_counts(rows, selected_tables)
    dbml_path = root / "schema.dbml"
    rules_path = root / "rules.yaml"
    dbml_path.write_text(_schema_dbml(selected_tables, signal_columns), encoding="utf-8")
    rules_path.write_text(_rules_yaml(selected_tables), encoding="utf-8")

    if "customers" in selected_tables:
        _write_csv(csv_dir / "customers.csv", _customers_rows(table_rows["customers"], seed))
    if "products" in selected_tables:
        _write_csv(csv_dir / "products.csv", _products_rows(table_rows["products"], seed))
    if "sellers" in selected_tables:
        _write_csv(csv_dir / "sellers.csv", _sellers_rows(table_rows["sellers"], seed))
    if "orders" in selected_tables:
        _write_csv(csv_dir / "orders.csv", _orders_rows(table_rows["orders"], table_rows, seed))
    if "order_reviews" in selected_tables:
        _write_csv(
            csv_dir / "order_reviews.csv",
            _order_reviews_rows(table_rows["order_reviews"], seed, signal_columns),
        )
    if "order_payments" in selected_tables:
        _write_csv(csv_dir / "order_payments.csv", _order_payments_rows(table_rows["order_payments"], seed))
    if "order_items" in selected_tables:
        _write_csv(csv_dir / "order_items.csv", _order_items_rows(table_rows["order_items"], table_rows, seed))
    if "shipments" in selected_tables:
        _write_csv(csv_dir / "shipments.csv", _shipments_rows(table_rows["shipments"], seed))
    if "support_tickets" in selected_tables:
        _write_csv(
            csv_dir / "support_tickets.csv",
            _support_tickets_rows(table_rows["support_tickets"], table_rows, seed),
        )
    if "inventory_events" in selected_tables:
        _write_csv(
            csv_dir / "inventory_events.csv",
            _inventory_events_rows(table_rows["inventory_events"], table_rows, seed),
        )

    return GeneratedBenchmarkDataset(
        root=root,
        dbml_path=dbml_path,
        csv_dir=csv_dir,
        rules_path=rules_path,
        target="order_reviews.review_score",
        requested_rows=rows,
        requested_tables=tables,
        seed=seed,
        signal_columns=signal_columns,
        table_rows=table_rows,
    )


def run_large_dataset_benchmark(
    *,
    work_dir: Path,
    rows: int = DEFAULT_BENCHMARK_ROWS,
    tables: int = DEFAULT_BENCHMARK_TABLES,
    max_analysis_rows: int = MAX_ANALYSIS_ROWS,
    max_feature_columns: int = MAX_FEATURE_COLUMNS,
    seed: int = DEFAULT_BENCHMARK_SEED,
    signal_columns: int = DEFAULT_SIGNAL_COLUMNS,
    force: bool = False,
    create_package: bool = True,
) -> dict[str, Any]:
    _validate_generator_args(rows=rows, tables=tables, signal_columns=signal_columns)
    _validate_limits(max_analysis_rows=max_analysis_rows, max_feature_columns=max_feature_columns)
    if work_dir.exists():
        if not force:
            raise ValueError(f"Benchmark work directory already exists: {work_dir}")
        shutil.rmtree(work_dir)
    input_dir = work_dir / "input"
    run_dir = work_dir / "run"
    package_dir = work_dir / "package"
    dataset = create_large_benchmark_dataset(
        root=input_dir,
        rows=rows,
        tables=tables,
        seed=seed,
        signal_columns=signal_columns,
        force=True,
    )

    started_at = _iso_now()
    wall_started = time.perf_counter()
    run_pipeline(
        dbml_path=dataset.dbml_path,
        csv_dir=dataset.csv_dir,
        rules_path=dataset.rules_path,
        target=dataset.target,
        out_dir=run_dir,
        max_analysis_rows=max_analysis_rows,
        max_feature_columns=max_feature_columns,
    )
    wall_seconds = round(time.perf_counter() - wall_started, 6)

    package_result: dict[str, Any] = {
        "enabled": create_package,
        "success": False,
        "output_dir": str(package_dir),
        "manifest_path": "",
        "index_path": "",
        "zip_path": "",
        "file_count": 0,
        "error": "",
    }
    if create_package:
        try:
            result = create_analysis_package(
                input_dir=run_dir,
                output_dir=package_dir,
                create_zip=True,
                force=True,
            )
        except Exception as exc:
            package_result["error"] = f"{exc.__class__.__name__}: {exc}"
        else:
            package_result.update(
                {
                    "success": True,
                    "output_dir": str(result.output_dir),
                    "manifest_path": str(result.manifest_path),
                    "index_path": str(result.index_path),
                    "zip_path": str(result.zip_path) if result.zip_path else "",
                    "file_count": result.file_count,
                }
            )

    report_path = run_dir / PERFORMANCE_GUARD_REPORT
    report = _build_performance_guard_report(
        dataset=dataset,
        run_dir=run_dir,
        work_dir=work_dir,
        started_at=started_at,
        wall_seconds=wall_seconds,
        max_analysis_rows=max_analysis_rows,
        max_feature_columns=max_feature_columns,
        package_result=package_result,
        artifact_audit={"status": "pending", "violations": []},
    )
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    zip_path_text = package_result.get("zip_path") or ""
    artifact_audit = audit_artifacts(
        run_dir=run_dir,
        package_dir=package_dir if create_package and package_dir.exists() else None,
        zip_path=Path(zip_path_text) if zip_path_text else None,
    )
    report = _build_performance_guard_report(
        dataset=dataset,
        run_dir=run_dir,
        work_dir=work_dir,
        started_at=started_at,
        wall_seconds=wall_seconds,
        max_analysis_rows=max_analysis_rows,
        max_feature_columns=max_feature_columns,
        package_result=package_result,
        artifact_audit=artifact_audit,
    )
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def scan_production_materialization_guards(src_root: Path | None = None) -> dict[str, Any]:
    root = src_root or Path(__file__).resolve().parent
    fetchdf_offenders: list[str] = []
    read_csv_offenders: list[str] = []
    pandas_import_offenders: list[str] = []
    allowed_pandas_imports = {"duckdb_utils.py", "influence_analyzer.py"}
    for path in sorted(root.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if path.name != "duckdb_utils.py" and FETCHDF_TOKEN in text:
            fetchdf_offenders.append(path.name)
        if PANDAS_READ_CSV_TOKEN in text or PD_READ_CSV_TOKEN in text:
            read_csv_offenders.append(path.name)
        if (
            (PANDAS_IMPORT_TOKEN in text or FROM_PANDAS_TOKEN in text)
            and path.name not in allowed_pandas_imports
        ):
            pandas_import_offenders.append(path.name)
    violations = [
        {"code": "UNGUARDED_FETCHDF", "files": fetchdf_offenders},
        {"code": "PANDAS_READ_CSV", "files": read_csv_offenders},
        {"code": "UNAPPROVED_PANDAS_IMPORT", "files": pandas_import_offenders},
    ]
    violations = [violation for violation in violations if violation["files"]]
    return {
        "status": "passed" if not violations else "failed",
        "src_root": str(root),
        "allowed_fetchdf_file": "duckdb_utils.py",
        "allowed_pandas_imports": sorted(allowed_pandas_imports),
        "violations": violations,
    }


def _build_performance_guard_report(
    *,
    dataset: GeneratedBenchmarkDataset,
    run_dir: Path,
    work_dir: Path,
    started_at: str,
    wall_seconds: float,
    max_analysis_rows: int,
    max_feature_columns: int,
    package_result: dict[str, Any],
    artifact_audit: dict[str, Any],
) -> dict[str, Any]:
    run_summary = _read_json(run_dir / "run_summary.json")
    run_events = _read_jsonl(run_dir / "run_events.jsonl")
    profile_summary = _read_json(run_dir / "profile_summary.json")
    influence = _read_json(run_dir / "influence.json")
    materialization = scan_production_materialization_guards()
    artifact_sizes = _artifact_sizes(run_dir)
    memory = _peak_rss_memory()
    chart_success = all((run_dir / path).is_file() for path in REQUIRED_CHARTS)
    report_success = (run_dir / "report.md").is_file() and (run_dir / "report.html").is_file()
    profile_rows = _profile_row_counts(profile_summary)
    limits = _limit_evidence(
        influence=influence,
        max_analysis_rows=max_analysis_rows,
        max_feature_columns=max_feature_columns,
    )
    package_success = bool(package_result.get("success"))
    violations = _benchmark_violations(
        run_summary=run_summary,
        chart_success=chart_success,
        report_success=report_success,
        package_success=package_success,
        audit=artifact_audit,
        materialization=materialization,
        limits=limits,
        memory=memory,
    )
    return {
        "artifact": "performance_guard_report",
        "version": 1,
        "status": "failed" if violations else "passed",
        "created_at": _iso_now(),
        "started_at": started_at,
        "work_dir": str(work_dir),
        "dataset": {
            "generator_version": GENERATOR_VERSION,
            "seed": dataset.seed,
            "requested_rows": dataset.requested_rows,
            "requested_tables": dataset.requested_tables,
            "signal_columns": dataset.signal_columns,
            "dbml_path": str(dataset.dbml_path),
            "csv_dir": str(dataset.csv_dir),
            "rules_path": str(dataset.rules_path),
            "target": dataset.target,
            "total_rows": dataset.total_rows,
            "tables": [
                {
                    "table": table,
                    "rows": rows,
                    "profile_rows": profile_rows.get(table),
                    "csv_path": str(dataset.csv_dir / f"{table}.csv"),
                    "size_bytes": (dataset.csv_dir / f"{table}.csv").stat().st_size,
                }
                for table, rows in dataset.table_rows.items()
            ],
        },
        "pipeline": {
            "output_dir": str(run_dir),
            "wall_seconds": wall_seconds,
            "run_summary_status": run_summary.get("status"),
            "run_summary_duration_seconds": run_summary.get("duration_seconds"),
            "stage_timings": run_summary.get("stage_timings", []),
            "run_event_count": len(run_events),
            "issue_count": (run_summary.get("issue_counts") or {}).get("total"),
        },
        "memory": memory,
        "limits": limits,
        "artifacts": {
            "total_size_bytes": sum(item["size_bytes"] for item in artifact_sizes),
            "file_count": len(artifact_sizes),
            "files": artifact_sizes,
            "chart_generation_success": chart_success,
            "report_generation_success": report_success,
            "required_charts": REQUIRED_CHARTS,
        },
        "package": package_result,
        "artifact_audit": artifact_audit,
        "materialization_guards": materialization,
        "violations": violations,
    }


def _limit_evidence(
    *,
    influence: dict[str, Any],
    max_analysis_rows: int,
    max_feature_columns: int,
) -> dict[str, Any]:
    notes = influence.get("notes") if isinstance(influence.get("notes"), list) else []
    top_features = influence.get("top_features") if isinstance(influence.get("top_features"), list) else []
    row_count = int(influence.get("row_count") or 0)
    feature_count = len(top_features)
    row_note = f"Influence dataframe limited to at most {max_analysis_rows} rows."
    feature_note = f"Influence dataframe limited to at most {max_feature_columns} feature columns."
    return {
        "max_analysis_rows": max_analysis_rows,
        "max_feature_columns": max_feature_columns,
        "postgres_chunk_rows_default": DEFAULT_POSTGRES_CHUNK_ROWS,
        "connector_chunking_applicable": False,
        "csv_scan_mode": "duckdb_read_csv_auto",
        "influence_row_count": row_count,
        "influence_top_feature_count": feature_count,
        "influence_notes": notes,
        "analysis_row_limit_enforced": row_count <= max_analysis_rows,
        "analysis_feature_limit_enforced": feature_count <= max_feature_columns,
        "analysis_row_limit_reported": row_note in notes,
        "analysis_feature_limit_reported": feature_note in notes,
        "feature_truncation_reported": any("Feature columns truncated" in str(note) for note in notes),
    }


def _benchmark_violations(
    *,
    run_summary: dict[str, Any],
    chart_success: bool,
    report_success: bool,
    package_success: bool,
    audit: dict[str, Any],
    materialization: dict[str, Any],
    limits: dict[str, Any],
    memory: dict[str, Any],
) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    if run_summary.get("status") != "success":
        violations.append({"code": "PIPELINE_NOT_SUCCESS", "message": "run_summary status is not success."})
    if not run_summary.get("stage_timings"):
        violations.append({"code": "STAGE_TIMINGS_MISSING", "message": "No stage timings were recorded."})
    if not chart_success:
        violations.append({"code": "CHARTS_MISSING", "message": "One or more required chart specs are missing."})
    if not report_success:
        violations.append({"code": "REPORTS_MISSING", "message": "report.md or report.html is missing."})
    if not package_success:
        violations.append({"code": "PACKAGE_FAILED", "message": "Export package was not created successfully."})
    if audit.get("status") != "passed":
        violations.append({"code": "ARTIFACT_AUDIT_FAILED", "message": "Artifact audit did not pass."})
    if materialization.get("status") != "passed":
        violations.append({"code": "MATERIALIZATION_GUARD_FAILED", "message": "Source scan found unsafe materialization usage."})
    for key in [
        "analysis_row_limit_enforced",
        "analysis_feature_limit_enforced",
        "analysis_row_limit_reported",
        "analysis_feature_limit_reported",
        "feature_truncation_reported",
    ]:
        if not limits.get(key):
            violations.append({"code": f"LIMIT_{key.upper()}_FALSE", "message": f"{key} is false."})
    if memory.get("supported") and memory.get("peak_rss_mb") is None:
        violations.append({"code": "PEAK_RSS_MISSING", "message": "Peak RSS is supported but missing."})
    return violations


def _validate_generator_args(*, rows: int, tables: int, signal_columns: int) -> None:
    if rows <= 0:
        raise ValueError("rows must be greater than zero")
    if tables < MIN_TABLE_COUNT or tables > len(TABLE_ORDER):
        raise ValueError(f"tables must be between {MIN_TABLE_COUNT} and {len(TABLE_ORDER)}")
    if signal_columns <= 0:
        raise ValueError("signal_columns must be greater than zero")


def _validate_limits(*, max_analysis_rows: int, max_feature_columns: int) -> None:
    if max_analysis_rows <= 0:
        raise ValueError("max_analysis_rows must be greater than zero")
    if max_feature_columns <= 0:
        raise ValueError("max_feature_columns must be greater than zero")


def _table_row_counts(rows: int, selected_tables: list[str]) -> dict[str, int]:
    counts = {
        "customers": max(10, rows // 8),
        "products": max(10, rows // 10),
        "sellers": max(5, rows // 20),
        "orders": rows,
        "order_reviews": rows,
        "order_payments": rows,
        "order_items": rows,
        "shipments": rows,
        "support_tickets": max(5, rows // 5),
        "inventory_events": rows,
    }
    return {table: counts[table] for table in selected_tables}


def _schema_dbml(selected_tables: list[str], signal_columns: int) -> str:
    blocks: list[str] = []
    if "customers" in selected_tables:
        blocks.append(
            """Table customers {
  customer_id varchar [pk, not null]
  customer_state varchar
  signup_segment varchar
}"""
        )
    if "products" in selected_tables:
        blocks.append(
            """Table products {
  product_id varchar [pk, not null]
  product_category_name varchar
  product_weight_g float
}"""
        )
    if "sellers" in selected_tables:
        blocks.append(
            """Table sellers {
  seller_id varchar [pk, not null]
  seller_state varchar
}"""
        )
    if "orders" in selected_tables:
        blocks.append(
            """Table orders {
  order_id varchar [pk, not null]
  customer_id varchar [ref: > customers.customer_id]
  order_status varchar
  order_purchase_timestamp timestamp
  order_delivered_customer_date timestamp
}"""
        )
    if "order_reviews" in selected_tables:
        signal_lines = "\n".join(f"  signal_{index:02d} float" for index in range(signal_columns))
        blocks.append(
            f"""Table order_reviews {{
  review_id varchar [pk, not null]
  order_id varchar [ref: > orders.order_id]
  review_score int
  review_comment_message varchar
{signal_lines}
}}"""
        )
    if "order_payments" in selected_tables:
        blocks.append(
            """Table order_payments {
  order_id varchar [ref: > orders.order_id]
  payment_sequential int
  payment_type varchar
  payment_installments int
  payment_value float
}"""
        )
    if "order_items" in selected_tables:
        blocks.append(
            """Table order_items {
  order_id varchar [ref: > orders.order_id]
  order_item_id int
  product_id varchar [ref: > products.product_id]
  seller_id varchar [ref: > sellers.seller_id]
  price float
  freight_value float

  indexes {
    (order_id, order_item_id) [pk]
  }
}"""
        )
    if "shipments" in selected_tables:
        blocks.append(
            """Table shipments {
  shipment_id varchar [pk, not null]
  order_id varchar [ref: > orders.order_id]
  carrier varchar
  shipped_at timestamp
  delivered_at timestamp
}"""
        )
    if "support_tickets" in selected_tables:
        blocks.append(
            """Table support_tickets {
  ticket_id varchar [pk, not null]
  order_id varchar [ref: > orders.order_id]
  customer_id varchar [ref: > customers.customer_id]
  category varchar
  response_hours float
  resolved varchar
}"""
        )
    if "inventory_events" in selected_tables:
        blocks.append(
            """Table inventory_events {
  event_id varchar [pk, not null]
  product_id varchar [ref: > products.product_id]
  event_type varchar
  adjustment_qty int
}"""
        )
    return "\n\n".join(blocks) + "\n"


def _rules_yaml(selected_tables: list[str]) -> str:
    sections = [
        """rules:
  order_reviews:
    - id: BENCH_REVIEW_SCORE_RANGE
      type: range
      column: review_score
      min: 1
      max: 5
      severity: P1""",
    ]
    if "order_payments" in selected_tables:
        sections.append(
            """  order_payments:
    - id: BENCH_PAYMENT_NON_NEGATIVE
      type: range
      column: payment_value
      min: 0
      severity: P1"""
        )
    if "orders" in selected_tables:
        sections.append(
            """  orders:
    - id: BENCH_DELIVERED_AFTER_PURCHASE
      type: expression
      columns:
        - order_purchase_timestamp
        - order_delivered_customer_date
      expression: "order_delivered_customer_date >= order_purchase_timestamp"
      severity: P1"""
        )
    if "order_items" in selected_tables:
        sections.append(
            """  order_items:
    - id: BENCH_PRICE_NON_NEGATIVE
      type: range
      column: price
      min: 0
      severity: P1"""
        )
    return "\n\n".join(sections) + "\n"


def _customers_rows(count: int, seed: int) -> Iterable[list[str]]:
    yield ["customer_id", "customer_state", "signup_segment"]
    states = ["SP", "RJ", "MG", "BA", "PR", "SC"]
    segments = ["new", "returning", "vip", "seasonal"]
    for index in range(count):
        yield [f"C{index:07d}", states[(index + seed) % len(states)], segments[index % len(segments)]]


def _products_rows(count: int, seed: int) -> Iterable[list[str]]:
    yield ["product_id", "product_category_name", "product_weight_g"]
    categories = ["books", "electronics", "home", "beauty", "sports", "toys"]
    for index in range(count):
        yield [f"P{index:07d}", categories[(index + seed) % len(categories)], str(100 + (index % 9000))]


def _sellers_rows(count: int, seed: int) -> Iterable[list[str]]:
    yield ["seller_id", "seller_state"]
    states = ["SP", "RJ", "MG", "PR"]
    for index in range(count):
        yield [f"S{index:07d}", states[(index + seed) % len(states)]]


def _orders_rows(count: int, table_rows: dict[str, int], seed: int) -> Iterable[list[str]]:
    yield [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_delivered_customer_date",
    ]
    customer_count = table_rows["customers"]
    statuses = ["delivered", "delivered", "delivered", "shipped", "processing"]
    base = datetime(2024, 1, 1, 8, 0, 0)
    for index in range(count):
        purchase = base + timedelta(minutes=index % 100_000)
        delivered = purchase + timedelta(days=2 + (index % 4))
        if index and index % 173 == 0:
            delivered = purchase - timedelta(days=1)
        customer_id = f"C{(index + seed) % customer_count:07d}"
        if index and index % 251 == 0:
            customer_id = "C9999999"
        yield [
            f"O{index:08d}",
            customer_id,
            statuses[index % len(statuses)],
            _dt(purchase),
            _dt(delivered),
        ]


def _order_reviews_rows(count: int, seed: int, signal_columns: int) -> Iterable[list[str]]:
    signal_headers = [f"signal_{index:02d}" for index in range(signal_columns)]
    yield ["review_id", "order_id", "review_score", "review_comment_message", *signal_headers]
    for index in range(count):
        score = (index % 5) + 1
        if index and index % 97 == 0:
            score = 9
        order_id = f"O{index:08d}"
        if index and index % 257 == 0:
            order_id = "O99999999"
        signals = [
            f"{round((score * (signal_index + 1)) + ((index + seed) % 13) / 10, 4):.4f}"
            for signal_index in range(signal_columns)
        ]
        yield [f"R{index:08d}", order_id, str(score), f"comment-{index % 11}", *signals]


def _order_payments_rows(count: int, seed: int) -> Iterable[list[str]]:
    yield ["order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value"]
    payment_types = ["credit_card", "voucher", "boleto", "debit_card"]
    for index in range(count):
        value = 20.0 + ((index + seed) % 500)
        if index and index % 211 == 0:
            value = -value
        yield [
            f"O{index:08d}",
            str((index % 3) + 1),
            payment_types[index % len(payment_types)],
            str((index % 6) + 1),
            f"{value:.2f}",
        ]


def _order_items_rows(count: int, table_rows: dict[str, int], seed: int) -> Iterable[list[str]]:
    yield ["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"]
    product_count = table_rows["products"]
    seller_count = table_rows["sellers"]
    for index in range(count):
        product_id = f"P{(index + seed) % product_count:07d}"
        seller_id = f"S{(index + seed) % seller_count:07d}"
        if index and index % 223 == 0:
            product_id = "P9999999"
        if index and index % 227 == 0:
            seller_id = "S9999999"
        price = 10.0 + (index % 1000)
        if index and index % 229 == 0:
            price = -price
        yield [f"O{index:08d}", "1", product_id, seller_id, f"{price:.2f}", f"{(price * 0.1):.2f}"]


def _shipments_rows(count: int, seed: int) -> Iterable[list[str]]:
    yield ["shipment_id", "order_id", "carrier", "shipped_at", "delivered_at"]
    carriers = ["alpha", "beta", "gamma"]
    base = datetime(2024, 1, 2, 9, 0, 0)
    for index in range(count):
        shipped = base + timedelta(minutes=index % 100_000)
        delivered = shipped + timedelta(days=1 + (index % 3))
        yield [f"SH{index:08d}", f"O{index:08d}", carriers[index % len(carriers)], _dt(shipped), _dt(delivered)]


def _support_tickets_rows(count: int, table_rows: dict[str, int], seed: int) -> Iterable[list[str]]:
    yield ["ticket_id", "order_id", "customer_id", "category", "response_hours", "resolved"]
    categories = ["delivery", "payment", "return", "product"]
    customer_count = table_rows["customers"]
    order_count = table_rows["orders"]
    for index in range(count):
        yield [
            f"T{index:08d}",
            f"O{(index * 3) % order_count:08d}",
            f"C{(index + seed) % customer_count:07d}",
            categories[index % len(categories)],
            f"{1.5 + (index % 72):.2f}",
            "true" if index % 7 else "false",
        ]


def _inventory_events_rows(count: int, table_rows: dict[str, int], seed: int) -> Iterable[list[str]]:
    yield ["event_id", "product_id", "event_type", "adjustment_qty"]
    event_types = ["received", "reserved", "returned", "damaged"]
    product_count = table_rows["products"]
    for index in range(count):
        adjustment = ((index + seed) % 31) - 10
        yield [
            f"IE{index:08d}",
            f"P{(index + seed) % product_count:07d}",
            event_types[index % len(event_types)],
            str(adjustment),
        ]


def _write_csv(path: Path, rows: Iterable[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def _profile_row_counts(profile_summary: dict[str, Any]) -> dict[str, int]:
    tables = profile_summary.get("tables")
    if not isinstance(tables, dict):
        return {}
    return {
        table: int(payload.get("row_count") or 0)
        for table, payload in tables.items()
        if isinstance(payload, dict)
    }


def _artifact_sizes(root: Path) -> list[dict[str, Any]]:
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        files.append({"path": _relative_posix(path, root), "size_bytes": path.stat().st_size})
    return files


def _peak_rss_memory() -> dict[str, Any]:
    try:
        import resource
    except Exception as exc:
        return {"supported": False, "peak_rss_mb": None, "source": "resource", "error": exc.__class__.__name__}
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        peak_mb = raw / (1024 * 1024)
        units = "bytes"
    else:
        peak_mb = raw / 1024
        units = "kilobytes"
    return {
        "supported": True,
        "peak_rss_mb": round(float(peak_mb), 3),
        "source": "resource.getrusage(RUSAGE_SELF).ru_maxrss",
        "raw_value": raw,
        "raw_units": units,
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _dt(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
