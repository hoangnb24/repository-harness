from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ForeignKey(BaseModel):
    parent_table: str
    parent_column: str


class ColumnSchema(BaseModel):
    name: str
    type: str
    is_pk: bool = False
    not_null: bool = False
    unique: bool = False
    foreign_key: ForeignKey | None = None


class TableSchema(BaseModel):
    name: str
    columns: dict[str, ColumnSchema] = Field(default_factory=dict)
    primary_key: list[str] = Field(default_factory=list)
    unique_constraints: list[list[str]] = Field(default_factory=list)


class Relationship(BaseModel):
    child_table: str
    child_column: str = ""
    parent_table: str
    parent_column: str = ""
    child_columns: list[str] = Field(default_factory=list)
    parent_columns: list[str] = Field(default_factory=list)
    dbml_operator: str = ">"
    declared_cardinality: str = "MANY_TO_ONE"
    relationship_type: str = "explicit_fk"

    @model_validator(mode="after")
    def _fill_compatibility_columns(self) -> Relationship:
        if not self.child_columns and self.child_column:
            self.child_columns = [self.child_column]
        if not self.parent_columns and self.parent_column:
            self.parent_columns = [self.parent_column]
        if not self.child_column and self.child_columns:
            self.child_column = self.child_columns[0]
        if not self.parent_column and self.parent_columns:
            self.parent_column = self.parent_columns[0]
        return self


class Schema(BaseModel):
    tables: dict[str, TableSchema] = Field(default_factory=dict)
    relationships: list[Relationship] = Field(default_factory=list)


class CatalogTable(BaseModel):
    table: str
    csv_path: Path
    columns: list[str]
    file_size_mb: float
    source_type: str = "csv"
    source_name: str | None = None


class CsvCatalog(BaseModel):
    tables: dict[str, CatalogTable] = Field(default_factory=dict)
    missing_tables: list[str] = Field(default_factory=list)
    extra_csvs: list[str] = Field(default_factory=list)


class ColumnProfile(BaseModel):
    name: str
    expected_type_from_dbml: str | None = None
    inferred_type: str
    null_count: int
    null_rate: float
    distinct_count: int
    top_10_values: list[dict[str, Any]] = Field(default_factory=list)
    min: Any | None = None
    max: Any | None = None
    mean: float | None = None
    std: float | None = None
    invalid_cast_count: int = 0


class TableProfile(BaseModel):
    table: str
    row_count: int
    column_count: int
    file_size_mb: float
    columns: dict[str, ColumnProfile] = Field(default_factory=dict)


class ProfileSummary(BaseModel):
    tables: dict[str, TableProfile] = Field(default_factory=dict)
    catalog: dict[str, Any] = Field(default_factory=dict)
    relationships: list[dict[str, Any]] = Field(default_factory=list)


class Issue(BaseModel):
    issue_id: str
    issue_type: str
    severity: str
    table: str
    columns: list[str]
    parent_table: str | None = None
    parent_columns: list[str] | None = None
    bad_count: int
    total_count: int
    bad_rate: float
    sample_bad_rows_path: str | None = None
    sample_keys: list[str] = Field(default_factory=list)
    evidence_sql: str
    probable_causes: list[str] = Field(default_factory=list)
    suggested_fix: list[str] = Field(default_factory=list)


class InfluenceFeature(BaseModel):
    feature: str
    score: float
    direction: str | None = None
    method: str
    interpretation: str


class InfluenceResult(BaseModel):
    target: str | None = None
    method: str = "association_not_causation"
    row_count: int = 0
    top_features: list[InfluenceFeature] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class RunEvent(BaseModel):
    sequence: int
    event_type: str
    timestamp: str
    run_id: str
    stage: str | None = None
    status: str | None = None
    duration_seconds: float | None = None
    artifact_path: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class RunStageSummary(BaseModel):
    name: str
    display_name: str
    status: str
    started_at: str
    finished_at: str | None = None
    duration_seconds: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None


class RunSummary(BaseModel):
    run_id: str
    status: str
    started_at: str
    output_dir: str
    finished_at: str | None = None
    duration_seconds: float | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    stage_timings: list[RunStageSummary] = Field(default_factory=list)
    issue_counts: dict[str, Any] = Field(default_factory=dict)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    skipped_stages: list[dict[str, Any]] = Field(default_factory=list)
    failed_stages: list[dict[str, Any]] = Field(default_factory=list)
    error: dict[str, str] | None = None
