from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import yaml

from vsf_profiler.models import (
    CatalogTable,
    CsvCatalog,
    CsvMappingCandidate,
    CsvMappingEvidence,
    Schema,
    TableSchema,
)


INFERRED_MAPPING_CONFIDENCE_THRESHOLD = 0.8
INFERRED_MAPPING_MARGIN = 0.12


@dataclass(frozen=True)
class _CsvFile:
    path: Path
    stem: str
    columns: list[str]
    file_size_mb: float


def build_catalog(
    csv_dir: str | Path,
    schema: Schema,
    *,
    mapping_overrides: dict[str, str] | None = None,
) -> CsvCatalog:
    root = Path(csv_dir)
    if not root.exists():
        raise FileNotFoundError(f"CSV directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"CSV path is not a directory: {root}")

    csv_files = [
        _CsvFile(
            path=path,
            stem=path.stem,
            columns=_read_header(path),
            file_size_mb=round(path.stat().st_size / (1024 * 1024), 4),
        )
        for path in sorted(root.glob("*.csv"))
    ]
    csv_by_stem = {file.stem: file for file in csv_files}
    overrides = _validate_overrides(mapping_overrides or {}, schema=schema)
    catalog = CsvCatalog()
    selected_stems: set[str] = set()

    all_candidates = {
        table_name: _mapping_candidates(table_name, table_schema, csv_files)
        for table_name, table_schema in schema.tables.items()
    }

    for table_name, override_value in overrides.items():
        csv_file = _resolve_override(override_value, csv_files)
        if csv_file.stem in selected_stems:
            raise ValueError(f"CSV mapping override selects {csv_file.path.name} more than once.")
        candidate = _candidate_for_file(all_candidates[table_name], csv_file)
        _select_mapping(
            catalog=catalog,
            table_name=table_name,
            csv_file=csv_file,
            evidence=_selected_evidence(
                table_name=table_name,
                mapping_method="manual",
                candidate=candidate,
                candidates=all_candidates[table_name],
                confidence=1.0,
            ),
        )
        selected_stems.add(csv_file.stem)

    for table_name in schema.tables:
        if table_name in catalog.tables:
            continue
        csv_file = csv_by_stem.get(table_name)
        if csv_file is None:
            continue
        if csv_file.stem in selected_stems:
            raise ValueError(f"CSV file {csv_file.path.name} is selected by more than one table.")
        candidate = _candidate_for_file(all_candidates[table_name], csv_file)
        _select_mapping(
            catalog=catalog,
            table_name=table_name,
            csv_file=csv_file,
            evidence=_selected_evidence(
                table_name=table_name,
                mapping_method="exact",
                candidate=candidate,
                candidates=all_candidates[table_name],
            ),
        )
        selected_stems.add(csv_file.stem)

    for table_name, table_schema in schema.tables.items():
        if table_name in catalog.tables:
            continue
        candidates = [
            candidate
            for candidate in all_candidates[table_name]
            if candidate.csv_stem not in selected_stems
        ]
        selected = _select_inferred_candidate(table_schema, candidates)
        if selected is not None:
            csv_file = csv_by_stem[selected.csv_stem]
            _select_mapping(
                catalog=catalog,
                table_name=table_name,
                csv_file=csv_file,
                evidence=_selected_evidence(
                    table_name=table_name,
                    mapping_method="inferred",
                    candidate=selected,
                    candidates=all_candidates[table_name],
                ),
            )
            selected_stems.add(csv_file.stem)
            continue

        catalog.missing_tables.append(table_name)
        catalog.mapping_evidence[table_name] = _unmapped_evidence(
            table_name=table_name,
            candidates=all_candidates[table_name],
        )

    catalog.extra_csvs = [
        file.stem
        for file in csv_files
        if file.stem not in selected_stems
    ]
    return catalog


def load_mapping_overrides(path: str | Path) -> dict[str, str]:
    override_path = Path(path)
    if not override_path.exists():
        raise FileNotFoundError(f"CSV mapping file does not exist: {override_path}")
    if not override_path.is_file():
        raise ValueError(f"CSV mapping path is not a file: {override_path}")
    if override_path.suffix.lower() == ".json":
        loaded = json.loads(override_path.read_text(encoding="utf-8"))
    else:
        loaded = yaml.safe_load(override_path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError("CSV mapping file must contain a mapping object.")
    raw = loaded.get("mappings", loaded)
    if not isinstance(raw, dict):
        raise ValueError("CSV mapping file 'mappings' value must be an object.")
    overrides: dict[str, str] = {}
    for table_name, csv_name in raw.items():
        if not isinstance(table_name, str) or not table_name.strip():
            raise ValueError("CSV mapping table names must be non-empty strings.")
        if not isinstance(csv_name, str) or not csv_name.strip():
            raise ValueError(f"CSV mapping for {table_name!r} must be a non-empty string.")
        overrides[table_name.strip()] = csv_name.strip()
    return overrides


def _read_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            return [column.lstrip("\ufeff") for column in next(reader)]
        except StopIteration:
            return []


def _validate_overrides(overrides: dict[str, str], *, schema: Schema) -> dict[str, str]:
    unknown = sorted(set(overrides) - set(schema.tables))
    if unknown:
        joined = ", ".join(unknown)
        raise ValueError(f"CSV mapping override references unknown DBML table(s): {joined}")
    return dict(overrides)


def _resolve_override(value: str, csv_files: list[_CsvFile]) -> _CsvFile:
    label = Path(value).name
    candidates = {
        file.path.name: file
        for file in csv_files
    }
    candidates.update({file.stem: file for file in csv_files})
    if not label.lower().endswith(".csv"):
        candidates.update({f"{file.stem}.csv": file for file in csv_files})
    resolved = candidates.get(label)
    if resolved is None:
        names = ", ".join(sorted(file.path.name for file in csv_files))
        raise ValueError(f"CSV mapping override references missing CSV {value!r}. Available: {names}")
    return resolved


def _mapping_candidates(
    table_name: str,
    table_schema: TableSchema,
    csv_files: list[_CsvFile],
) -> list[CsvMappingCandidate]:
    candidates = [
        _score_candidate(table_name, table_schema, csv_file)
        for csv_file in csv_files
    ]
    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.confidence,
            candidate.column_overlap,
            candidate.filename_similarity,
            -len(candidate.extra_columns),
            candidate.csv_stem,
        ),
        reverse=True,
    )


def _score_candidate(
    table_name: str,
    table_schema: TableSchema,
    csv_file: _CsvFile,
) -> CsvMappingCandidate:
    dbml_columns = list(table_schema.columns)
    dbml_normalized = {_normalize_identifier(column): column for column in dbml_columns}
    csv_normalized = {_normalize_identifier(column): column for column in csv_file.columns}
    matched_columns = [
        column
        for column in dbml_columns
        if _normalize_identifier(column) in csv_normalized
    ]
    missing_columns = [
        column
        for column in dbml_columns
        if _normalize_identifier(column) not in csv_normalized
    ]
    extra_columns = [
        column
        for column in csv_file.columns
        if _normalize_identifier(column) not in dbml_normalized
    ]

    filename_similarity = (
        1.0
        if csv_file.stem == table_name
        else SequenceMatcher(
            None,
            _normalize_identifier(table_name),
            _normalize_identifier(csv_file.stem),
        ).ratio()
    )
    column_overlap = _safe_ratio(len(matched_columns), len(dbml_columns))
    primary_key_match = _match_ratio(table_schema.primary_key, csv_normalized)
    foreign_key_columns = [
        column.name
        for column in table_schema.columns.values()
        if column.foreign_key
    ]
    foreign_key_match = _match_ratio(foreign_key_columns, csv_normalized)
    extra_column_penalty = _safe_ratio(len(extra_columns), len(csv_file.columns))
    confidence = (
        (0.20 * filename_similarity)
        + (0.55 * column_overlap)
        + (0.15 * primary_key_match)
        + (0.10 * foreign_key_match)
        - (0.15 * extra_column_penalty)
    )

    return CsvMappingCandidate(
        csv_path=csv_file.path.name,
        csv_stem=csv_file.stem,
        confidence=round(max(0.0, min(1.0, confidence)), 4),
        filename_similarity=round(filename_similarity, 4),
        column_overlap=round(column_overlap, 4),
        primary_key_match=round(primary_key_match, 4),
        foreign_key_match=round(foreign_key_match, 4),
        extra_column_penalty=round(extra_column_penalty, 4),
        matched_columns=matched_columns,
        missing_columns=missing_columns,
        extra_columns=extra_columns,
        is_exact_filename=csv_file.stem == table_name,
    )


def _candidate_for_file(
    candidates: list[CsvMappingCandidate],
    csv_file: _CsvFile,
) -> CsvMappingCandidate:
    for candidate in candidates:
        if candidate.csv_stem == csv_file.stem:
            return candidate
    raise ValueError(f"No mapping candidate was scored for {csv_file.path.name}.")


def _select_inferred_candidate(
    table_schema: TableSchema,
    candidates: list[CsvMappingCandidate],
) -> CsvMappingCandidate | None:
    if not candidates:
        return None
    top = candidates[0]
    second = candidates[1] if len(candidates) > 1 else None
    if top.confidence < INFERRED_MAPPING_CONFIDENCE_THRESHOLD:
        return None
    if second is not None and top.confidence - second.confidence < INFERRED_MAPPING_MARGIN:
        return None
    if top.column_overlap < 0.75:
        return None
    if not _has_disambiguating_header(table_schema, top):
        return None
    return top


def _has_disambiguating_header(
    table_schema: TableSchema,
    candidate: CsvMappingCandidate,
) -> bool:
    if len(candidate.matched_columns) >= 2:
        return True
    if table_schema.primary_key and candidate.primary_key_match >= 1.0:
        return True
    foreign_key_columns = [
        column.name
        for column in table_schema.columns.values()
        if column.foreign_key
    ]
    return bool(foreign_key_columns and candidate.foreign_key_match >= 1.0)


def _selected_evidence(
    *,
    table_name: str,
    mapping_method: str,
    candidate: CsvMappingCandidate,
    candidates: list[CsvMappingCandidate],
    confidence: float | None = None,
) -> CsvMappingEvidence:
    return CsvMappingEvidence(
        table=table_name,
        status="mapped",
        mapping_method=mapping_method,
        confidence=round(candidate.confidence if confidence is None else confidence, 4),
        selected_csv=candidate.csv_path,
        candidates=candidates,
        matched_columns=candidate.matched_columns,
        missing_columns=candidate.missing_columns,
        extra_columns=candidate.extra_columns,
    )


def _unmapped_evidence(
    *,
    table_name: str,
    candidates: list[CsvMappingCandidate],
) -> CsvMappingEvidence:
    top = candidates[0] if candidates else None
    second = candidates[1] if len(candidates) > 1 else None
    ambiguous = (
        top is not None
        and top.confidence >= INFERRED_MAPPING_CONFIDENCE_THRESHOLD
        and second is not None
        and top.confidence - second.confidence < INFERRED_MAPPING_MARGIN
    )
    return CsvMappingEvidence(
        table=table_name,
        status="ambiguous" if ambiguous else "missing_csv",
        mapping_method="ambiguous" if ambiguous else "unmapped",
        confidence=top.confidence if top else 0.0,
        selected_csv=None,
        ambiguity_reason=(
            "Top mapping candidates are too close to auto-select."
            if ambiguous
            else "No candidate met the inferred mapping threshold."
        ),
        candidates=candidates,
        matched_columns=top.matched_columns if top else [],
        missing_columns=top.missing_columns if top else list(),
        extra_columns=top.extra_columns if top else [],
    )


def _select_mapping(
    *,
    catalog: CsvCatalog,
    table_name: str,
    csv_file: _CsvFile,
    evidence: CsvMappingEvidence,
) -> None:
    catalog.tables[table_name] = CatalogTable(
        table=table_name,
        csv_path=csv_file.path,
        columns=csv_file.columns,
        file_size_mb=csv_file.file_size_mb,
        mapping_method=evidence.mapping_method,
        mapping_confidence=evidence.confidence,
    )
    catalog.mapping_evidence[table_name] = evidence


def _normalize_identifier(value: str) -> str:
    return "".join(char for char in value.casefold() if char.isalnum())


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return numerator / denominator


def _match_ratio(expected_columns: list[str], csv_normalized: dict[str, str]) -> float:
    if not expected_columns:
        return 1.0
    matched = sum(1 for column in expected_columns if _normalize_identifier(column) in csv_normalized)
    return matched / len(expected_columns)
