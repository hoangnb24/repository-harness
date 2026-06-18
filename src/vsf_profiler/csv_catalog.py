from __future__ import annotations

import csv
from pathlib import Path

from vsf_profiler.models import CatalogTable, CsvCatalog, Schema


def build_catalog(csv_dir: str | Path, schema: Schema) -> CsvCatalog:
    root = Path(csv_dir)
    if not root.exists():
        raise FileNotFoundError(f"CSV directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"CSV path is not a directory: {root}")

    csv_files = {path.stem: path for path in sorted(root.glob("*.csv"))}
    catalog = CsvCatalog()

    for table_name in schema.tables:
        path = csv_files.get(table_name)
        if not path:
            catalog.missing_tables.append(table_name)
            continue
        catalog.tables[table_name] = CatalogTable(
            table=table_name,
            csv_path=path,
            columns=_read_header(path),
            file_size_mb=round(path.stat().st_size / (1024 * 1024), 4),
        )

    catalog.extra_csvs = [name for name in csv_files if name not in schema.tables]
    return catalog


def _read_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            return [column.lstrip("\ufeff") for column in next(reader)]
        except StopIteration:
            return []
