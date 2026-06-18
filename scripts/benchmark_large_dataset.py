from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from vsf_profiler.large_benchmark import (
    DEFAULT_BENCHMARK_ROWS,
    DEFAULT_BENCHMARK_SEED,
    DEFAULT_BENCHMARK_TABLES,
    DEFAULT_SIGNAL_COLUMNS,
    PERFORMANCE_GUARD_REPORT,
    run_large_dataset_benchmark,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a deterministic VSF Data Profiler large-dataset benchmark."
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path("outputs/benchmark_large"),
        help="Benchmark work directory containing generated inputs, run output, and package.",
    )
    parser.add_argument("--rows", type=int, default=DEFAULT_BENCHMARK_ROWS, help="Order-grain rows to generate.")
    parser.add_argument(
        "--tables",
        type=int,
        default=DEFAULT_BENCHMARK_TABLES,
        help="Number of relational tables to generate.",
    )
    parser.add_argument(
        "--max-analysis-rows",
        type=int,
        default=1_000,
        help="Maximum rows materialized for bounded influence analysis.",
    )
    parser.add_argument(
        "--max-feature-columns",
        type=int,
        default=8,
        help="Maximum feature columns materialized for bounded influence analysis.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_BENCHMARK_SEED, help="Deterministic seed.")
    parser.add_argument(
        "--signal-columns",
        type=int,
        default=DEFAULT_SIGNAL_COLUMNS,
        help="Signal feature columns generated on order_reviews.",
    )
    parser.add_argument(
        "--no-package",
        action="store_true",
        help="Skip package and zip generation.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing benchmark work directory.",
    )
    args = parser.parse_args(argv)

    report = run_large_dataset_benchmark(
        work_dir=args.work_dir,
        rows=args.rows,
        tables=args.tables,
        max_analysis_rows=args.max_analysis_rows,
        max_feature_columns=args.max_feature_columns,
        seed=args.seed,
        signal_columns=args.signal_columns,
        force=args.force,
        create_package=not args.no_package,
    )
    report_path = args.work_dir / "run" / PERFORMANCE_GUARD_REPORT
    print(json.dumps({"status": report["status"], "report_path": str(report_path)}, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
