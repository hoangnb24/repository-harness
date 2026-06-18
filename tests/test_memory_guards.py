import csv
from pathlib import Path

import pytest

from vsf_profiler.csv_catalog import build_catalog
from vsf_profiler.dbml_parser import parse_dbml
from vsf_profiler.duckdb_utils import connect, fetch_bounded_df
from vsf_profiler.influence_analyzer import analyze_influence


def test_fetch_bounded_df_enforces_row_and_column_limits():
    con = connect()
    try:
        frame = fetch_bounded_df(
            con,
            "SELECT i AS value FROM range(100) AS data(i)",
            max_rows=7,
            max_columns=1,
        )
        assert len(frame) == 7
        assert list(frame.columns) == ["value"]

        with pytest.raises(ValueError, match="exceeding max_columns=1"):
            fetch_bounded_df(
                con,
                "SELECT 1 AS first_value, 2 AS second_value",
                max_rows=10,
                max_columns=1,
            )
    finally:
        con.close()


def test_influence_analysis_uses_bounded_frame_for_largeish_csv(tmp_path):
    feature_count = 24
    row_count = 1_500
    root = tmp_path / "largeish"
    csv_dir = root / "csv"
    csv_dir.mkdir(parents=True)
    schema_path = root / "schema.dbml"
    csv_path = csv_dir / "observations.csv"
    feature_names = [f"feature_{index:02d}" for index in range(feature_count)]

    schema_path.write_text(
        "\n".join(
            [
                "Table observations {",
                "  observation_id varchar [pk, not null]",
                "  target float",
                *[f"  {feature_name} float" for feature_name in feature_names],
                "}",
            ]
        )
    )
    with csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["observation_id", "target", *feature_names])
        for row_index in range(row_count):
            target = float(row_index % 10)
            writer.writerow(
                [
                    f"obs-{row_index:05d}",
                    target,
                    *[
                        round(target * (feature_index + 1) + (row_index % 3), 3)
                        for feature_index in range(feature_count)
                    ],
                ]
            )

    schema = parse_dbml(schema_path)
    catalog = build_catalog(csv_dir, schema)
    con = connect()
    try:
        result = analyze_influence(
            con=con,
            schema=schema,
            catalog=catalog,
            target="observations.target",
            max_analysis_rows=40,
            max_feature_columns=5,
        )
    finally:
        con.close()

    assert result.row_count == 40
    assert "Influence dataframe limited to at most 40 rows." in result.notes
    assert "Influence dataframe limited to at most 5 feature columns." in result.notes
    assert any("Feature columns truncated from 24 candidates to 5 selected" in note for note in result.notes)
    assert result.top_features
    assert {
        feature.feature
        for feature in result.top_features
    }.issubset({"feature_00", "feature_01", "feature_02", "feature_03", "feature_04"})


def test_production_duckdb_to_pandas_calls_go_through_bounded_helper():
    src_root = Path(__file__).resolve().parents[1] / "src" / "vsf_profiler"
    offenders = []
    for path in src_root.glob("*.py"):
        if path.name == "duckdb_utils.py":
            continue
        if ".fetchdf(" in path.read_text():
            offenders.append(path.name)
    assert offenders == []


def test_production_pandas_usage_is_limited_to_bounded_analysis_modules():
    src_root = Path(__file__).resolve().parents[1] / "src" / "vsf_profiler"
    allowed_imports = {"duckdb_utils.py", "influence_analyzer.py"}
    import_offenders = []
    read_csv_offenders = []
    for path in src_root.glob("*.py"):
        text = path.read_text()
        if ("import pandas" in text or "from pandas" in text) and path.name not in allowed_imports:
            import_offenders.append(path.name)
        if "pandas.read_csv" in text or "pd.read_csv" in text:
            read_csv_offenders.append(path.name)

    assert import_offenders == []
    assert read_csv_offenders == []
