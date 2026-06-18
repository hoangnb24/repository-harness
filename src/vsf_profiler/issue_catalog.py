from __future__ import annotations

from pathlib import Path

import duckdb

from vsf_profiler.duckdb_utils import run_scalar, safe_rate, sql_literal
from vsf_profiler.models import Issue


CAUSES = {
    "TABLE_MISSING": ["CSV extract did not include a table required by the DBML contract."],
    "COLUMN_MISSING": ["CSV header is missing a column required by the DBML contract."],
    "EXTRA_COLUMN": ["CSV extract includes a column not declared in the DBML contract."],
    "TYPE_CAST_INVALID": ["Source data contains values that do not match the declared DBML type."],
    "REQUIRED_FIELD_NULL": ["Required source field was emitted as null or blank."],
    "PRIMARY_KEY_NULL": ["Primary key generation or extraction produced null or blank keys."],
    "DUPLICATE_PRIMARY_KEY": ["Primary key uniqueness is not enforced before export."],
    "UNIQUE_DUPLICATE": ["Unique field has duplicate values in the CSV extract."],
    "ORPHAN_FOREIGN_KEY": [
        "Parent table may be missing a batch.",
        "Child rows may have loaded before parent rows.",
        "Join key transformation may be inconsistent across tables.",
    ],
    "PARENT_KEY_DUPLICATE": ["Parent key is not unique, so joins can multiply child rows."],
    "CHILD_RELATIONSHIP_DUPLICATE": [
        "Child foreign-key values are not unique for a declared one-to-one relationship."
    ],
    "VALUE_OUT_OF_RANGE": ["A business rule range constraint was violated."],
    "NEGATIVE_VALUE_NOT_ALLOWED": ["A non-negative amount rule was violated."],
    "DATE_ORDER_INVALID": ["Timestamp ordering violates the expected business process."],
    "ACCEPTED_VALUE_VIOLATION": ["A categorical column contains undeclared values."],
    "REGEX_MISMATCH": ["A text value does not match the expected pattern."],
    "EMPTY_STRING": ["Text fields contain blank strings that may behave differently from null."],
    "INVALID_PLACEHOLDER_TOKEN": ["Placeholder tokens are present instead of normalized nulls."],
    "NUMERIC_OUTLIER": ["Numeric values fall outside the profiled IQR fence for this column."],
}

FIXES = {
    "TABLE_MISSING": ["Regenerate the extract with all DBML tables included."],
    "COLUMN_MISSING": ["Update the export query or DBML contract so headers match."],
    "EXTRA_COLUMN": ["Confirm whether the DBML contract needs this column or remove it from export."],
    "TYPE_CAST_INVALID": ["Normalize source values before export and quarantine uncastable rows."],
    "REQUIRED_FIELD_NULL": ["Add a not-null validation before publish and backfill missing values."],
    "PRIMARY_KEY_NULL": ["Reject rows with missing primary keys before downstream joins."],
    "DUPLICATE_PRIMARY_KEY": ["Deduplicate by primary key or fix upstream key generation."],
    "UNIQUE_DUPLICATE": ["Audit the uniqueness contract and deduplicate upstream records."],
    "ORPHAN_FOREIGN_KEY": [
        "Check the parent table load pipeline.",
        "Add anti-join validation before publish.",
        "Quarantine child rows whose parent key is missing.",
    ],
    "PARENT_KEY_DUPLICATE": ["Deduplicate parent keys before using the table as a dimension."],
    "CHILD_RELATIONSHIP_DUPLICATE": [
        "Deduplicate child foreign-key values or change the DBML relationship cardinality."
    ],
    "VALUE_OUT_OF_RANGE": ["Clamp, reject, or correct values outside the accepted business range."],
    "NEGATIVE_VALUE_NOT_ALLOWED": ["Reject negative amount rows or correct sign handling upstream."],
    "DATE_ORDER_INVALID": ["Fix timestamp derivation and add ordering validation in the pipeline."],
    "ACCEPTED_VALUE_VIOLATION": ["Update the allowed set or normalize unexpected category values."],
    "REGEX_MISMATCH": ["Normalize the text field or update the regex if the contract changed."],
    "EMPTY_STRING": ["Convert blank strings to null or enforce non-empty text rules."],
    "INVALID_PLACEHOLDER_TOKEN": ["Normalize placeholder tokens to null at ingestion."],
    "NUMERIC_OUTLIER": [
        "Review bounded sample rows and decide whether to correct, cap, transform, or keep the values."
    ],
}


class IssueCatalog:
    def __init__(self, samples_dir: Path, con: duckdb.DuckDBPyConnection | None = None) -> None:
        self.samples_dir = samples_dir
        self.samples_dir.mkdir(parents=True, exist_ok=True)
        self.con = con
        self._counter = 0
        self.issues: list[Issue] = []

    def add_issue(
        self,
        *,
        issue_type: str,
        severity: str,
        table: str,
        columns: list[str],
        bad_count: int,
        total_count: int,
        evidence_sql: str,
        parent_table: str | None = None,
        parent_columns: list[str] | None = None,
        sample_sql: str | None = None,
        sample_key_sql: str | None = None,
        probable_causes: list[str] | None = None,
        suggested_fix: list[str] | None = None,
    ) -> Issue | None:
        if bad_count <= 0:
            return None

        self._counter += 1
        issue_id = f"ISSUE-{self._counter:04d}"
        sample_path = None
        if sample_sql and self.con is not None:
            sample_path = self.samples_dir / f"{issue_id}.csv"
            self._write_sample(sample_sql, sample_path)
        sample_path_for_issue = None
        if sample_path:
            try:
                sample_path_for_issue = str(sample_path.relative_to(self.samples_dir.parent))
            except ValueError:
                sample_path_for_issue = str(sample_path)

        sample_keys: list[str] = []
        if sample_key_sql and self.con is not None:
            try:
                rows = self.con.execute(sample_key_sql).fetchall()
                sample_keys = [str(row[0]) for row in rows if row and row[0] is not None]
            except duckdb.Error:
                sample_keys = []

        issue = Issue(
            issue_id=issue_id,
            issue_type=issue_type,
            severity=severity,
            table=table,
            columns=columns,
            parent_table=parent_table,
            parent_columns=parent_columns,
            bad_count=int(bad_count),
            total_count=int(total_count),
            bad_rate=round(safe_rate(int(bad_count), int(total_count)), 6),
            sample_bad_rows_path=sample_path_for_issue,
            sample_keys=sample_keys,
            evidence_sql=evidence_sql.strip(),
            probable_causes=probable_causes or CAUSES.get(issue_type, ["Data violates the current contract."]),
            suggested_fix=suggested_fix or FIXES.get(issue_type, ["Inspect sample rows and update the pipeline."]),
        )
        self.issues.append(issue)
        return issue

    def add_count_issue(
        self,
        *,
        issue_type: str,
        severity: str,
        table: str,
        columns: list[str],
        total_count: int,
        count_sql: str,
        sample_sql: str | None = None,
        parent_table: str | None = None,
        parent_columns: list[str] | None = None,
        sample_key_sql: str | None = None,
    ) -> Issue | None:
        if self.con is None:
            raise RuntimeError("add_count_issue requires a DuckDB connection")
        bad_count = int(run_scalar(self.con, count_sql, 0))
        return self.add_issue(
            issue_type=issue_type,
            severity=severity,
            table=table,
            columns=columns,
            parent_table=parent_table,
            parent_columns=parent_columns,
            bad_count=bad_count,
            total_count=total_count,
            evidence_sql=count_sql,
            sample_sql=sample_sql,
            sample_key_sql=sample_key_sql,
        )

    def _write_sample(self, sample_sql: str, sample_path: Path) -> None:
        try:
            copy_sql = f"COPY ({sample_sql}) TO {sql_literal(sample_path)} (HEADER, DELIMITER ',')"
            self.con.execute(copy_sql)
        except duckdb.Error:
            sample_path.write_text("sample_error\n")
