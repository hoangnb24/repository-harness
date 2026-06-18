from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from vsf_profiler.artifact_audit import audit_artifacts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit VSF Data Profiler run and package artifacts."
    )
    parser.add_argument("--run-dir", required=True, type=Path, help="Profiler output directory.")
    parser.add_argument(
        "--package-dir",
        type=Path,
        default=None,
        help="Optional self-contained package directory.",
    )
    parser.add_argument(
        "--zip-path",
        type=Path,
        default=None,
        help="Optional package zip archive.",
    )
    args = parser.parse_args(argv)
    report = audit_artifacts(
        run_dir=args.run_dir,
        package_dir=args.package_dir,
        zip_path=args.zip_path,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
